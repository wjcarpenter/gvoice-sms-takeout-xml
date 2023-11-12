from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings
warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)
from bs4.element import Comment
import re
import os
from fs.path import basename
import phonenumbers
import dateutil.parser
import datetime
from calendar import timegm
import base64
from io import open # adds emoji support
import json
import isodate
import argparse

__updated__ = "2023-11-12 13:34"

# SMS Backup and Restore likes to notice filename that start with "sms-"
# Save it to the great-grandparent directory because it can otherwise be hard to find amongst
# the zillion HTML files. The great-grandparent directory is the one that contains
# "Takeout" as a subdirectory, and you should run this script from the
# Takeout/Voice/Calls subdirectory.

sms_backup_filename  = "../../../sms-gvoice-all.xml"
call_backup_filename = "../../../calls-gvoice-all.xml"
vm_backup_filename   = "../../../sms-vm-gvoice-all.xml"
sms_backup_file  = None
call_backup_file = None
vm_backup_file   = None

# We sometimes see isolated messages from ourselves to someone, and the Takeout format
# only identifies them by contact name instead of phone number. In such cases, we
# consult this optional JSON file to map  the name to a phone number (which should
# include the "+" and country code and no other punctuation). Must be valid JSON, eg:
# {
#   "Me": "+441234567890",
#   "Joe Blow": "+18885551234",
#   "Susie Glow": "+18885554321"
# }
# In cases where there is no JSON entry when needed, a warning is printed. Update
# the JSON file and re-run this script. Don't try to restore with the output
# file until you have resolved all of those contacts_keyed_by_name warnings.

# This file is *optional* unless you get an error message asking you to add entries to it.
contacts_filename = "../../../contacts.json"
# The contacts JSON file, if present, is read into this dictionary, but discovered entries are also read into it.
contacts_keyed_by_name = dict()
# You can probably guess what this is based on the name. It's the inverse of the one just above.
contacts_keyed_by_number = dict()

# this is for some internal bookkeeping; you don't need to do anything with it.
missing_contacts = set()
conflicting_contacts = dict()

# some global counters for a stats summary at the end
counters = {
    'number_of_sms_output':    0, 
    'number_of_calls_output':  0, 
    "number_of_vms_output":    0,
    "contacts_read_from_file": 0,
    "conflict_warnings":       0,
    "todo_errors":             0,
    "first_pass_defers":       0
    }

# I really don't like globals, but there are just too many things to tote around in all these function calls.
phone_number_from_filename = None
contact_name_from_filename = None
phone_number_from_html_title = None
contact_name_from_html_title = None
html_elt = None
verbosity = 0
VERBOSE = 0
QUIET = -1
VERY_QUIET = -2
ATTACHMENT_TYPE_IMAGE = "image"
ATTACHMENT_TYPE_AUDIO = "audio"
ATTACHMENT_TYPE_VCARD = "vcard"

# My convention is to use a relative filename when emitting into the XML
# and an absolute filename when printing a message for the person running the script.

def main():
    global sms_backup_file, vm_backup_file, call_backup_file
    global sms_backup_filename, vm_backup_filename, call_backup_filename, contacts_filename
    global html_elt, verbosity
    
    
    description = f'Convert Google Takeout HTML files to SMS Backup and Restore XML files. (Version {__updated__})'
    epilog = ('All command line arguments are optional and have reasonable defaults when run from within "Takeout/Voice/Calls/". '
        'The contacts file is optional. '
        'Output files should be named "sms-SOMETHING.xml" or "calls-SOMETHING.xml". '
        "See the README at https://github.com/wjcarpenter/gvoice-sms-takeout-xml for more information.")
    argparser = argparse.ArgumentParser(description=description, epilog=epilog)
    argparser.add_argument('-s', '--sms_backup_filename',  
                           default=sms_backup_filename,  
                           help=f"File to receive SMS/MMS messages. Defaults to {sms_backup_filename}")
    argparser.add_argument('-v', '--vm_backup_filename',   
                           default=vm_backup_filename,   
                           help=f"File to receive voicemail MMS messages. Defaults to {vm_backup_filename}")
    argparser.add_argument('-c', '--call_backup_filename', 
                           default=call_backup_filename, 
                           help=f"File to receive call history records. Defaults to {call_backup_filename}")
    argparser.add_argument('-j', '--contacts_filename',    
                           default=contacts_filename,    
                           help=f'JSON formatted file of contact name/number pairs. Defaults to {contacts_filename}')
    argparser.add_argument('-d', '--directory',            
                           default=".",                  
                           help=f'The directory containing the HTML files, typically the "Takeout/Voice/Calls/" subdirectory. Defaults to the current directory.')
    argparser.add_argument('-q', '--quiet',                
                           default=0,                    
                           help="Be a little quieter. Give this flag twice to be very quiet.", 
                           action='count')
    args = vars(argparser.parse_args())

    sms_backup_filename = args['sms_backup_filename']
    vm_backup_filename = args['vm_backup_filename']
    call_backup_filename = args['call_backup_filename']
    directory = args['directory']
    contacts_filename = args['contacts_filename']
    # I wanted to let users choose the level of quietness, but I found it
    # counterintuitive to use that value in the code, so I simply negate it
    # and call it verbosity. Such is the mind of a programmer.
    verbosity = -args['quiet']
    
    prep_output_files()
    if verbosity >= VERBOSE:
        print('>> Reading *.html files under', get_aka_path(directory))
    come_back_later = []
    
    with (open(sms_backup_filename, 'w') as sms_backup_file, 
          open(vm_backup_filename, 'w') as vm_backup_file, 
          open(call_backup_filename, 'w') as call_backup_file):
        
        write_dummy_headers()
        for subdirectory, dirs, files in os.walk(directory):
            for html_basename in files:
                html_target = (subdirectory, html_basename)
                process_one_file(True, html_target, come_back_later)

        me_contact = contacts_keyed_by_name.get('Me', None)
        if not me_contact and come_back_later:
            print()
            print("Unfortunately, we can't figure out your own phone number.")
            print(os.path.abspath(contacts_filename) + ': TODO: add a +phonenumber for contact: "Me": "+",')
            counters['todo_errors'] += 1
        else:
            if verbosity >= VERBOSE:
                print(">> Your 'Me' phone number is", me_contact)
            for html_target in come_back_later:
                process_one_file(False, html_target, come_back_later)

        write_trailers()
    
    # we have to reopen the files with a different mode for this
    write_real_headers()
    print_counters()

def process_one_file(is_first_pass, html_target, come_back_later):
    global html_elt
    __, html_basename = html_target
    if not html_basename.endswith('.html'): return
    
    get_name_or_number_from_filename(html_basename)
    with open(get_rel_path(html_target), 'r', encoding="utf-8") as html_file:
        html_elt = BeautifulSoup(html_file, 'html.parser')
    get_name_or_number_from_title()

    tags_div = html_elt.body.find(class_='tags')
    tag_elts = tags_div.find_all(rel='tag')
    tag_values = set()
    for tag_elt in tag_elts:
        tag_value = tag_elt.get_text()
        tag_values.add(tag_value)

    scan_vcards_for_contacts(html_target, html_elt.body)
    need_title_contact = contact_name_from_html_title and not contacts_keyed_by_name.get(contact_name_from_html_title, None)
    need_filename_contact = contact_name_from_filename and not contacts_keyed_by_name.get(contact_name_from_filename, None)
    me_contact = contacts_keyed_by_name.get('Me', None)
    if is_first_pass and (not me_contact or need_title_contact or need_filename_contact):
        if "Text" in tag_values or "Voicemail" in tag_values or "Recorded" in tag_values:
            # Can't do anything rational for SMS/MMS if we don't know our own number.
            # We _might_ be able to get along without the phone numbers for the contacts
            # named in the filename or the HTML title, but not always. Save them for
            # the second pass just in case.
            if verbosity >= QUIET:
                print(">> Deferring:", get_abs_path(html_target))
            counters['first_pass_defers'] += 1
            come_back_later.append(html_target)
            return

    if not is_first_pass:
        if verbosity >= QUIET:
            print(">> 2nd  pass:", get_abs_path(html_target))
        # Need to be firmer about mapping contact names to numbers! The contact_name_to_number() function will complain.
        if contact_name_from_html_title and not contact_name_to_number(html_target, contact_name_from_html_title):
            return
        if contact_name_from_filename and not contact_name_to_number(html_target, contact_name_from_filename):
            return

    if   "Text"      in tag_values:  process_Text_from_html_file(html_target)
    elif "Received"  in tag_values:  process_call_from_html_file(html_target, 1)
    elif "Placed"    in tag_values:  process_call_from_html_file(html_target, 2)
    elif "Missed"    in tag_values:  process_call_from_html_file(html_target, 3)
    elif "Voicemail" in tag_values:  process_Voicemail_from_html_file(html_target)
    elif "Recorded"  in tag_values:  process_Voicemail_from_html_file(html_target)
    else:
        print(f"Unrecognized tag_value situation '{tag_values}'; silently ignoring file '{get_abs_path(html_target)}'")

def process_Text_from_html_file(html_target):
    # A single HTML file can contain arbitrarily many SMS or MMS messages. I don't *think*
    # a single HTML file can have a mix of SMS and MMS since an HTML for MMS has a global
    # "participants" list.
    # MMS can be either with or without attachments.
    message_elts = html_elt.find_all(class_='message')
    participants_elt = html_elt.find(class_='participants')

    if participants_elt:
        write_mms_messages(html_target, participants_elt, message_elts)
    else:
        write_sms_messages(html_target, message_elts)

def process_Voicemail_from_html_file(html_target):
    # For a voicemail, we write a call record and also an MMS record with the recording attached.
    # The app doesn't like type 4 (voicemail) in a call record, so we emit type 3 (missed call),
    # which is kinda sorta correct.
    process_call_from_html_file(html_target, 3)
    write_mms_message_for_vm(html_target)

def process_call_from_html_file(html_target, call_type):
    contributor_elt = html_elt.body.find(class_="contributor")
    tel_elt = contributor_elt.find(class_="tel")
    telephone_number_full = tel_elt.attrs['href']
    telephone_number_suffix = telephone_number_full[4:]
    if not telephone_number_suffix:
        presentation = '2'
    else:
        presentation = '1'
    telephone_number = format_number(html_target, telephone_number_suffix)

    published_elt = html_elt.body.find(class_="published")
    readable_date = published_elt.get_text().replace("\r"," ").replace("\n"," ")
    iso_date = published_elt.attrs['title']
    timestamp = get_time_unix(html_elt.body)
    duration_elt = html_elt.find(class_="duration")
    if not duration_elt:
        duration = 0
    else:
        iso_duration = duration_elt.attrs['title']
        duration = isodate.parse_duration(iso_duration)
        duration = round(datetime.timedelta.total_seconds(duration))
    write_call_message(html_target, telephone_number, presentation, duration, timestamp, call_type, readable_date)

def contact_name_to_number(html_target, contact_name):
    if not contact_name:
        print("TODO: We can't figure out the contact name or number from an HTML file. Using '0'.")
        print(f'      due to File: "{get_abs_path(html_target)}"')
        return "0"
    contact_number = contacts_keyed_by_name.get(contact_name, None)
    if not contact_number and not contact_name in missing_contacts:
        print()
        print(f'TODO: {os.path.abspath(contacts_filename)}: add a +phonenumber for contact: "{contact_name}": "+",')
        print(f'      due to File: "{get_abs_path(html_target)}"')
        counters['todo_errors'] += 1
        # we add this fake entry to a dictionary so we don't keep complaining about the same thing
        missing_contacts.add(contact_name)
    return contact_number

def contact_number_to_name(contact_number):
    return contacts_keyed_by_number.get(contact_number, None)

def get_sender_number_from_title_or_filename(html_target):
    if phone_number_from_html_title:
        sender = phone_number_from_html_title
    elif contact_name_from_html_title:
        sender = contact_name_to_number(html_target, contact_name_from_html_title)
    elif phone_number_from_filename:
        sender = phone_number_from_filename
    elif contact_name_from_filename:
        sender = contact_name_to_number(html_target, contact_name_from_filename)
    else:
        sender = None
    return sender

def write_call_message(html_target, telephone_number, presentation, duration, timestamp, call_type, readable_date):
    parent_elt = BeautifulSoup()
    parent_elt.append(bs4_get_file_comment(html_target))
    bs4_append_call_elt(parent_elt, telephone_number, duration, timestamp, presentation, readable_date, call_type)
    call_backup_file.write(parent_elt.prettify())
    call_backup_file.write('\n')
    counters['number_of_calls_output'] += 1

def write_sms_messages(html_target, message_elts):
    other_party_number = None
    # Since the "address" element of an SMS is always the other end, scan the
    # message elements until we find a number this not "Me". Use that as the
    # address value for all of the SMS files in this HTML.
    for message_elt in message_elts:
        if other_party_number:
            break
        other_party_number = scan_vcards_for_contacts(html_target, message_elt)

    # This will be the case if the HTML file contains only a single SMS
    # that was sent by "Me". Use fallbacks.
    if not other_party_number:
        other_party_number = get_sender_number_from_title_or_filename(html_target)

    for message_elt in message_elts:
        the_text = get_message_text(message_elt)
        message_type = get_message_type(message_elt)
        sent_by_me = (message_type == 2)
        timestamp = get_time_unix(message_elt)
        attachment_elts = get_attachment_elts(message_elt)
        parent_elt = BeautifulSoup()
        parent_elt.append(bs4_get_file_comment(html_target))
        # if it was just an attachment with no text, there is no point in creating an empty SMS to go with it
        if the_text and the_text != "MMS Sent" and not attachment_elts:
            bs4_append_sms_elt(parent_elt, other_party_number, timestamp, the_text, message_type)
        else:
            msgbox_type = message_type
            bs4_append_mms_elt_with_parts(parent_elt, html_target, attachment_elts, the_text, other_party_number, sent_by_me, timestamp, msgbox_type, [other_party_number])
        sms_backup_file.write(parent_elt.prettify())
        sms_backup_file.write('\n')
        counters['number_of_sms_output'] += 1

def write_mms_message_for_vm(html_target):
    # We want to end up with an MMS messages, just like any other, but the HTML input file is 
    # significantly different, so we have this bit of voodoo where we fake up some of the stuff.
    sender = None
    sender_name = None
    body_elt = html_elt.find('body')
    contributor_elt = body_elt.find(class_='contributor')
    this_number, this_name = get_number_and_name_from_tel_elt_parent(contributor_elt)
    if this_number:
        sender = this_number
        sender_name = this_name
    if not sender:
        sender = get_sender_number_from_title_or_filename(html_target)
    if not sender_name:
        sender_name = contact_number_to_name(sender)

    participants = [sender] if sender else ["0"]
    timestamp = get_time_unix(body_elt)
    vm_from = (sender_name if sender_name else sender if sender else "Unknown")
    transcript = get_vm_transcript(body_elt)
    if transcript:
        the_text = "Voicemail/Recording from: " + vm_from + ";\nTranscript: " + transcript
    else:
        the_text = "Voicemail/Recording from: " + vm_from        
    attachment_elts = get_attachment_elts(body_elt)
    msgbox_type = '1' # 1 = Received, 2 = Sent
    sent_by_me = False
    parent_elt = BeautifulSoup()
    parent_elt.append(bs4_get_file_comment(html_target))
    bs4_append_mms_elt_with_parts(parent_elt, html_target, attachment_elts, the_text, sender, sent_by_me, timestamp, msgbox_type, participants)
    vm_backup_file.write(parent_elt.prettify())
    vm_backup_file.write('\n')
    counters['number_of_vms_output'] += 1

def write_mms_messages(html_target, participants_elt, message_elts):
    participants = get_mms_participant_phone_numbers(html_target, participants_elt)

    for message_elt in message_elts:
        # TODO who is sender?
        not_me_vcard_number = scan_vcards_for_contacts(html_target, message_elt)
        sender = not_me_vcard_number
        sent_by_me = sender not in participants
        the_text = get_message_text(message_elt)
        message_type = get_message_type(message_elt)
        timestamp = get_time_unix(message_elt)
        attachment_elts = get_attachment_elts(message_elt)

        parent_elt = BeautifulSoup()
        parent_elt.append(bs4_get_file_comment(html_target))
        bs4_append_mms_elt_with_parts(parent_elt, html_target, attachment_elts, the_text, sender, sent_by_me, timestamp, None, participants)
        sms_backup_file.write(parent_elt.prettify())
        sms_backup_file.write('\n')
        counters['number_of_sms_output'] += 1

def get_attachment_elts(message_elt):
    attachment_elts = []
    div_elts = message_elt.find_all('div')
    for div_elt in div_elts:
        img_elt = div_elt.find('img')
        if img_elt:
            attachment_elts.append(img_elt)
        audio_elt = div_elt.find('audio')
        if audio_elt:
            attachment_elts.append(audio_elt)
        vcard_elt = div_elt.find(class_='vcard')
        # distinguish between a vCard that is attached vs a vcard element that is just info from Takeout
        if vcard_elt and vcard_elt.name == "a":
            attachment_elts.append(vcard_elt)
    return attachment_elts

def bs4_append_sms_elt(parent_elt, sender, timestamp, the_text, message_type):
    sms_elt = html_elt.new_tag('sms')
    parent_elt.append(sms_elt)

    # protocol - Protocol used by the message, its mostly 0 in case of SMS messages.
    sms_elt['protocol'] = '0'
    # address - The phone number of the sender/recipient.
    sms_elt['address'] = sender
    # date - The Java date representation (including millisecond) of the time when the message was sent/received.
    sms_elt['date'] = timestamp
    # type - 1 = Received, 2 = Sent, 3 = Draft, 4 = Outbox, 5 = Failed, 6 = Queued
    sms_elt['type'] = message_type
    # subject - Subject of the message, its always null in case of SMS messages.
    sms_elt['subject'] = 'null'
    # body - The content of the message.
    sms_elt['body'] = the_text
    # toa - n/a, defaults to null.
    sms_elt['toa'] = 'null'
    # sc_toa - n/a, defaults to null.
    sms_elt['sc_toa'] = 'null'
    # service_center - The service center for the received message, null in case of sent messages.
    sms_elt['service_center'] = 'null'
    # read - Read Message = 1, Unread Message = 0.
    sms_elt['read'] = '1'
    # status - None = -1, Complete = 0, Pending = 32, Failed = 64.
    sms_elt['status'] = '1'
    sms_elt['locked'] = '0'

    # sub_id - Optional field that has the id of the phone subscription (SIM).
    # readable_date - Optional field that has the date in a human readable format.
    # contact_name - Optional field that has the name of the contact.

def bs4_append_mms_elt_with_parts(parent_elt, html_target, attachment_elts, the_text, other_party_number, sent_by_me, timestamp, msgbox_type, participants):
    m_type = 128 if sent_by_me else 132
    bs4_append_mms_elt(parent_elt, participants, timestamp, m_type, msgbox_type, other_party_number, sent_by_me, the_text)
    mms_elt = parent_elt.mms

    if attachment_elts:
        parts_elt = mms_elt.parts
        for sequence_number, attachment_elt in enumerate(attachment_elts):
            if attachment_elt.name == 'img':
                attachment_file_ref = attachment_elt['src']
                bs4_append_part_elt(parts_elt, ATTACHMENT_TYPE_IMAGE, sequence_number, html_target, attachment_file_ref)
            elif attachment_elt.name == 'audio':
                attachment_file_ref = attachment_elt.a['href']
                bs4_append_part_elt(parts_elt, ATTACHMENT_TYPE_AUDIO, sequence_number, html_target, attachment_file_ref)
            elif attachment_elt.name == 'a' and 'vcard' in attachment_elt['class']:
                attachment_file_ref = attachment_elt['href']
                bs4_append_part_elt(parts_elt, ATTACHMENT_TYPE_VCARD, sequence_number, html_target, attachment_file_ref)
            else:
                print(f'>> Unrecognized MMS attachment in HTML file (skipped):\n>> {attachment_elt}')
                print(f'>>     due to File: "{get_abs_path(html_target)}"')

def bs4_append_mms_elt(parent_elt, participants, timestamp, m_type, msgbox_type, other_party_number, sent_by_me, the_text):
    mms_elt = html_elt.new_tag('mms')
    parent_elt.append(mms_elt)

    bs4_append_addrs_elt(mms_elt, participants, other_party_number, sent_by_me)

    parts_elt = html_elt.new_tag('parts')
    mms_elt.append(parts_elt)
    bs4_append_text_part_elt(parts_elt, the_text)
    
    participants_tilde = '~'.join(participants)
    # address - The phone number of the sender/recipient.
    mms_elt['address'] = participants_tilde
    # ct_t - The Content-Type of the message, usually "application/vnd.wap.multipart.related"
    mms_elt['ct_t'] = 'application/vnd.wap.multipart.related'
    # date - The Java date representation (including millisecond) of the time when the message was sent/received.
    mms_elt['date'] = timestamp
    # m_type - The type of the message defined by MMS spec.
    mms_elt['m_type'] = m_type
    # msg_box - The type of message, 1 = Received, 2 = Sent, 3 = Draft, 4 = Outbox
    mms_elt['msg_box'] = msgbox_type
    # read - Has the message been read
    mms_elt['read'] = '1'
    # rr - The read-report of the message.
    mms_elt['rr'] = '129'
    mms_elt['seen'] = '1'
    mms_elt['sub_id'] = '-1'
    mms_elt['text_only'] = '0'

    # sub - The subject of the message, if present.
    # m_id - The Message-ID of the message
    # m_size - The size of the message.
    # sim_slot - The sim card slot.
    # readable_date - Optional field that has the date in a human readable format.
    # contact_name - Optional field that has the name of the contact.
    
    return parent_elt

def bs4_append_text_part_elt(elt_parent, the_text):
    if not the_text or the_text == "MMS Sent":
        return  # don't bother with this trivial text part 

    text_part_elt = html_elt.new_tag('part')

    # seq - The order of the part.
    text_part_elt['seq'] = '-1'
    # ct - The content type of the part.
    text_part_elt['ct'] = 'text/plain'
    # name - The name of the part.
    text_part_elt['name'] = 'null'
    # chset - The charset of the part.
    text_part_elt['chset'] = '106'
    text_part_elt['cd'] = 'null'
    text_part_elt['fn'] = 'null'
    text_part_elt['cid'] = '<text000001>'
    # cl - The content location of the part.
    text_part_elt['cl'] = 'text000001'
    text_part_elt['ctt_s'] = 'null'
    text_part_elt['ctt_t'] = 'null'
    # text - The text content of the part.
    text_part_elt['text'] = the_text
    elt_parent.append(text_part_elt)

    # data - The base64 encoded binary content of the part.

def bs4_append_part_elt(parent_elt, attachment_type, sequence_number, html_target, attachment_file_ref):
    attachment_filename, content_type = figure_out_attachment_filename_and_type(attachment_type, html_target, attachment_file_ref)
    subdirectory, __ = html_target
    if attachment_filename:
        attachment_filename_rel_path = get_rel_path((subdirectory, attachment_filename))
        with open(attachment_filename_rel_path, 'rb') as attachment_file: 
            attachment_data = base64.b64encode(attachment_file.read()).decode()
        parent_elt.append(bs4_get_file_comment((subdirectory, attachment_filename)))
        part_elt = html_elt.new_tag('part')
        parent_elt.append(part_elt)

        # seq - The order of the part.
        part_elt['seq'] = sequence_number
        # ct - The content type of the part.
        part_elt['ct'] = content_type
        # name - The name of the part.
        part_elt['name'] = attachment_filename
        # chset - The charset of the part.
        part_elt['chset'] = 'null'
        part_elt['cd'] = 'null'
        part_elt['fn'] = 'null'
        part_elt['cid'] = '<0>'
        part_elt['ctt_s'] = 'null'
        part_elt['ctt_t'] = 'null'
        # text - The text content of the part.
        part_elt['text'] = 'null'
        part_elt['sef_type'] = '0'
        # cl - The content location of the part.
        part_elt['cl'] = attachment_filename
        # data - The base64 encoded binary content of the part.
        part_elt['data'] = attachment_data

def bs4_append_addrs_elt(elt_parent, participants, other_party_number, sent_by_me):
    addrs_elt = html_elt.new_tag('addrs')
    elt_parent.append(addrs_elt)
    me_contact = contacts_keyed_by_name.get("Me")
    for participant in participants + [me_contact]:
        if sent_by_me and participant == me_contact:
            participant_is_sender = True
        elif not sent_by_me and participant == other_party_number:
            participant_is_sender = True
        else:
            participant_is_sender = False
        addr_elt = html_elt.new_tag('addr')

        # address - The phone number of the sender/recipient.
        addr_elt['address'] = participant
        # charset - Character set of this entry
        addr_elt['charset'] = '106'
        # type - The type of address, 129 = BCC, 130 = CC, 151 = To, 137 = From
        addr_elt['type'] = 137 if participant_is_sender else 151

        addrs_elt.append(addr_elt)

def bs4_append_call_elt(parent_elt, telephone_number, duration, timestamp, presentation, readable_date, call_type):
    call_elt = html_elt.new_tag('call')
    # number - The phone number of the call.
    call_elt['number'] = telephone_number
    # duration - The duration of the call in seconds.
    call_elt['duration'] = duration
    # date - The Java date representation (including millisecond) of the time of the call
    call_elt['date'] = timestamp
    # presentation - caller id presentation info. 1 = Allowed, 2 = Restricted, 3 = Unknown, 4 = Payphone.
    call_elt['presentation'] = presentation
    # readable_date - Optional field that has the date in a human readable format.
    call_elt['readable_date'] = readable_date    
    # call_type - 1 = Incoming, 2 = Outgoing, 3 = Missed, 4 = Voicemail, 5 = Rejected, 6 = Refused List.
    call_elt['type'] = call_type    
    #call_elt['post_dial_digits'] = ''
    # subscription_id - Optional field that has the id of the phone subscription (SIM). On some phones these are values like 0, 1, 2  etc. based on how the phone assigns the index to the sim being used while others have the full SIM ID.
    # contact_name - Optional field that has the name of the contact.
    
    parent_elt.append(call_elt)

def bs4_get_file_comment(file_target):
    return Comment(f' file: "{get_rel_path(file_target)}" ')

def figure_out_attachment_filename_and_type(attachment_type, html_target, attachment_file_ref):
    # Why don't we try the filename with the extension first? We only know how to handle
    # specific types of attachments, and we'll find those trhough trial and error pasting
    # various extensions back onto the basename, so trying the existing extension first
    # doesn't get us anything except weird special cases that we can't handle.
    subdirectory, html_basename = html_target
    # We assume all attachment references are relative to the directory of the HTML file.
    base, __ = os.path.splitext(attachment_file_ref)
    attachment_filename, content_type = consider_this_attachment_file_candidate(subdirectory, base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    base = base[:50]  # this is odd; probably bugs in Takeout or at least weird choices
    attachment_filename, content_type = consider_this_attachment_file_candidate(subdirectory, base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    base, __ = os.path.splitext(html_basename)
    attachment_filename, content_type = consider_this_attachment_file_candidate(subdirectory, base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type
        
    base = base[:50]  # this is odd; probably bugs in Takeout or at least weird choices
    attachment_filename, content_type = consider_this_attachment_file_candidate(subdirectory, base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    print(f'>> {attachment_type} attachment referenced in HTML file but not found (skipped); partial name: "{get_abs_path((subdirectory, attachment_file_ref))}"')
    print(f'>>    src="{attachment_file_ref}"')
    print(f'>>    due to File: "{get_abs_path(html_target)}"')
    return None, None
    
def consider_this_attachment_file_candidate(subdirectory, base, attachment_type):
    attachment_filename = None
    content_type = None
    if attachment_type == ATTACHMENT_TYPE_IMAGE:
        if os.path.exists(get_rel_path((subdirectory, base + '.jpg'))):
            attachment_filename = base + '.jpg'
            content_type = 'image/jpeg'
        elif os.path.exists(get_rel_path((subdirectory, base + '.gif'))):
            attachment_filename = base + '.gif'
            content_type = 'image/gif'
        elif os.path.exists(get_rel_path((subdirectory, base + '.png'))):
            attachment_filename = base + '.png'
            content_type = 'image/png'
    elif attachment_type == ATTACHMENT_TYPE_AUDIO:
        if os.path.exists(get_rel_path((subdirectory, base + '.mp3'))):
            attachment_filename = base + '.mp3'
            content_type = 'audio/mp3'
    elif attachment_type == ATTACHMENT_TYPE_VCARD:
        if os.path.exists(get_rel_path((subdirectory, base + '.vcf'))):
            attachment_filename = base + '.vcf'
            content_type = 'text/x-vCard'
    return attachment_filename, content_type
    
# One of the mysteries for Takeout formatting. If the <cite> element includes a
# <span> tag, then it was sent by someone else. If no <span> tag, it was sent by Me.
def get_message_type(message):
    cite_elt = message.cite
    if cite_elt.span:
        return 1
    else:
        return 2

def get_vm_transcript(message_elt):
    full_text_elt = message_elt.find(class_='full-text')
    if not full_text_elt:
        return None
    
    return BeautifulSoup(full_text_elt.text, 'html.parser').prettify().strip()

def get_message_text(message_elt):
    text_elt = message_elt.find('q')
    if not text_elt:
        return None
    return text_elt.text

def get_mms_participant_phone_numbers(html_target, participants_elt):
    participants = []
    tel_elts = participants_elt.find_all(class_='tel')
    for tel_elt in tel_elts:
        if not tel_elt.name == 'a':
            continue
        raw_number = tel_elt['href'][4:]
        if not raw_number:
            # I don't know if this can ever happen
            raw_number = contact_name_to_number(get_sender_number_from_title_or_filename(html_target))
        phone_number = format_number(html_target, raw_number)
        participants.append(format_number(html_target, phone_number))

    if participants == []:
        # The filename for an MMS is just "Group Conversation", which is worthless for here.
        if phone_number_from_html_title is None:
            phone_number_from_html_title = contact_name_to_number(contact_name_from_html_title)
        participants.append(contact_name_to_number(phone_number_from_html_title))
                
    return participants

def format_number(html_target, raw_number):
    try:
        phone_number = phonenumbers.parse(raw_number, None)
    except phonenumbers.phonenumberutil.NumberParseException:
        # I also saw this on a 10-year-old "Placed" call. Probably a data glitch.
        if verbosity >= QUIET:
            print()
            if not raw_number:
                print(f"TODO: Missing contact phone number in HTML file. Using '0'.")
                raw_number = '0'
            else:
                print(f"TODO: Possibly malformed contact phone number '{raw_number}' in HTML file. Using it anyhow.")
            print(f'      due to File: "{get_abs_path(html_target)}"')
        counters['todo_errors'] += 1
        return raw_number
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

def get_time_unix(message):
    time_elt = message.find(class_='dt')
    if not time_elt:
        time_elt = message.find(class_='published')
    iso_time = time_elt['title']
    time_obj = dateutil.parser.isoparse(iso_time);
    mstime = timegm(time_obj.timetuple()) * 1000 + time_obj.microsecond / 1000
    return int(mstime)

def get_aka_path(path):
    if os.path.isabs(path):
        return path
    else:
        return path + f', aka {os.path.abspath(path)}'

def get_abs_path(target):
    rel_path = get_rel_path(target)
    return os.path.abspath(rel_path)    

def get_rel_path(target):
    subdirectory, basename = target
    return os.path.normpath(os.path.join(subdirectory, basename))

xml_header = u"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n"
def write_dummy_headers():
    # The extra padding on the "count" lines are so that we can write the real count later
    # without worrying about not having enough space. The extra whitespace at that
    # place in the XML file is not significant.
    sms_backup_file.write(xml_header)
    sms_backup_file.write(u'<smses count="0">                                           \n')
    sms_backup_file.write(u"<!--Converted from GV Takeout data -->\n")

    ################
    vm_backup_file.write(xml_header)
    vm_backup_file.write(u'<smses count="0">                                           \n')
    vm_backup_file.write(u"<!--Converted from GV Takeout data -->\n")

    ################
    call_backup_file.write(xml_header)
    call_backup_file.write(u'<calls count="0">                                           \n')
    call_backup_file.write(u"<!--Converted from GV Takeout data -->\n")

def print_counters():
    if verbosity >= QUIET:
        print(f">> {counters['number_of_sms_output']:6} SMS/MMS records written to {sms_backup_filename}")
        print(f">> {counters['number_of_vms_output']:6} Voicemail records written to {vm_backup_filename}")
        print(f">> {counters['number_of_calls_output']:6} Call records written to {call_backup_filename}")
        contacts_from_json = counters['contacts_read_from_file']
        print(f">> {contacts_from_json:6} Contact name-and-numbers read from JSON file {contacts_filename}")
        contacts_from_html = len(contacts_keyed_by_name) - contacts_from_json
        print(f">> {contacts_from_html:6} Contact name-and-numbers discovered in HTML files")
        print(f">> {counters['first_pass_defers']:6} Files deferred on first pass")
        print(f">> {counters['conflict_warnings']:6} Conflict warnings given")
        print(f">> {counters['todo_errors']:6} TODO errors given")
    
def write_real_headers():
    print()

    with open(sms_backup_filename, 'r+') as backup_file:
        backup_file.write(xml_header)
        backup_file.write(f'<smses count={counters["number_of_sms_output"]}>\n')

    ################
    with open(vm_backup_filename, 'r+') as backup_file:
        backup_file.write(xml_header)
        backup_file.write(f'<smses count={counters["number_of_vms_output"]}>\n')

    ################
    with open(call_backup_filename, 'r+') as backup_file:
        backup_file.write(xml_header)
        backup_file.write(f'<calls count={counters["number_of_calls_output"]}>\n')

def write_trailers():
    sms_backup_file.write(u'</smses>\n')
    vm_backup_file.write(u'</smses>\n')
    call_backup_file.write(u'</calls>\n')

def prep_output_files():
    global contacts_keyed_by_name
    sms_backup_filename_BAK = sms_backup_filename + '.BAK'
    if os.path.exists(sms_backup_filename):
        if os.path.exists(sms_backup_filename_BAK):
            if verbosity >= VERBOSE:
                print('>> Removing', os.path.abspath(sms_backup_filename_BAK))
            os.remove(sms_backup_filename_BAK)
        if verbosity >= VERBOSE:
            print('>> Renaming existing SMS/MMS output file to', os.path.abspath(sms_backup_filename_BAK))
        os.rename(sms_backup_filename, sms_backup_filename_BAK)

    if verbosity >= VERBOSE:
        print('>> SMS/MMS will be written to',  get_aka_path(sms_backup_filename))
        print(">>")

    call_backup_filename_BAK = call_backup_filename + '.BAK'
    if os.path.exists(call_backup_filename):
        if os.path.exists(call_backup_filename_BAK):
            if verbosity >= VERBOSE:
                print('>> Removing', os.path.abspath(call_backup_filename_BAK))
            os.remove(call_backup_filename_BAK)
        if verbosity >= VERBOSE:
            print('>> Renaming existing Calls output file to', os.path.abspath(call_backup_filename_BAK))
        os.rename(call_backup_filename, call_backup_filename_BAK)

    if verbosity >= VERBOSE:
        print('>> Call history will be written to', get_aka_path(call_backup_filename))
        print(">>")

    vm_backup_filename_BAK = vm_backup_filename + '.BAK'
    if os.path.exists(vm_backup_filename):
        if os.path.exists(vm_backup_filename_BAK):
            if verbosity >= VERBOSE:
                print('>> Removing', os.path.abspath(vm_backup_filename_BAK))
            os.remove(vm_backup_filename_BAK)
        if verbosity >= VERBOSE:
            print('>> Renaming existing Voicemail output file to', os.path.abspath(vm_backup_filename_BAK))
        os.rename(vm_backup_filename, vm_backup_filename_BAK)

    if verbosity >= VERBOSE:
        print('>> Voicemail MMS will be written to', get_aka_path(vm_backup_filename))
        print(">>")

    # OK, this isn't an output file. So sue me.
    if os.path.exists(contacts_filename):
        with open(contacts_filename) as cnf: 
            cn_data = cnf.read() 
            contacts_keyed_by_name = json.loads(cn_data)
            for name, number in contacts_keyed_by_name.items():
                contacts_keyed_by_number[number] = name
            counters['contacts_read_from_file'] = len(contacts_keyed_by_name)
            if verbosity >= VERBOSE:
                print('>> Reading contacts from JSON contacts file', os.path.abspath(contacts_filename))
    else:
            if verbosity >= VERBOSE:
                print('>> No (optional) JSON contacts file', os.path.abspath(contacts_filename))

    if verbosity >= VERBOSE:
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

# In some extreme cases, we have to pick our the correspondent from the name
# of the file. It can be a phone number or a contact name, or it can be completely missing.
def get_name_or_number_from_filename(html_basename):
    global phone_number_from_filename, contact_name_from_filename
    phone_number_from_filename = None
    contact_name_from_filename = None
    # phone number with optional "+"
    match_phone_number = re.match(r'(\+?[0-9]+) - ', html_basename)
    if match_phone_number:
        phone_number_from_filename = match_phone_number.group(1)
    else:
        # sometimes a single " - ", sometimes two of them
        match_name = re.match(r'([^ ].*) - .+ - ', html_basename)
        if not match_name:
            match_name = re.match(r'([^ ].*) - ', html_basename)
        if match_name:
            contact_name_from_filename = match_name.group(1)
            if contact_name_from_filename == "Group Conversation":
                contact_name_from_filename = None

def get_name_or_number_from_title():
    global phone_number_from_html_title, contact_name_from_html_title
    phone_number_from_html_title = None
    contact_name_from_html_title = None
    title_elt = html_elt.find('head').find('title')
    title_value = title_elt.get_text()
    # Takeout puts a newline in the middle of the title
    split = title_value.split("\n")
    correspondent = split[len(split)-1].strip()
    
    if not correspondent:
        return

    match_phone_number = re.match(r'(\+?[0-9]+)', correspondent)
    if match_phone_number:
        # I think this doesn't actually happen
        phone_number_from_html_title = match_phone_number.group(1)
    else:
        contact_name_from_html_title = correspondent
        if contact_name_from_html_title == "Group Conversation":
            contact_name_from_html_title = None

# Iterate all of the vcards in the HTML body to speculatively populate the
# contacts list. Also make a note of a contact which is "not me" for
# use as the address in an SMS record (it's always "the other end"). The
# same logic does not apply to MMS, which has a different scheme for address.
def scan_vcards_for_contacts(html_target, parent_elt):
    global me
    not_me_vcard_number = None
    vcard_elts = parent_elt.find_all(class_="vcard")
    for vcard_elt in vcard_elts:
        this_number, this_name = get_number_and_name_from_tel_elt_parent(vcard_elt)
        if this_number:
            if this_name != "Me":
                not_me_vcard_number = this_number
            # In case of conflicts, last writer wins
            if this_name:
                existing_number = contacts_keyed_by_name.get(this_name, None)
                contacts_keyed_by_name[this_name] = this_number
                contacts_keyed_by_number[this_number] = this_name
                if existing_number and this_number != existing_number:
                    conflict_set = conflicting_contacts.get(this_name, None)
                    if not conflict_set:
                        conflict_set = set()
                        conflict_set.add(existing_number)
                    if not this_number in conflict_set:
                        if verbosity >= QUIET:
                            print(f'>> Info: conflicting information about "{this_name}":', this_number, conflict_set)
                            print(f'>>    due to File: "{get_abs_path(html_target)}"')
                        counters['conflict_warnings'] += 1
                        conflict_set.add(this_number)
                    conflicting_contacts[this_name] = conflict_set
    return not_me_vcard_number

def get_number_and_name_from_tel_elt_parent(parent_elt):
    this_name = None
    this_number = None
    tel_elt = parent_elt.find(class_='tel')
    if not tel_elt:
        return None, None
    href_attr = tel_elt['href']
    if href_attr:
        if href_attr.startswith("tel:"):
            href_attr = href_attr[4:]
        if not href_attr:
            return None, None  # this shouldn't happen
        this_number = href_attr
        fn_elt = parent_elt.find(class_="fn")
        if not fn_elt:
            return this_number, None
        this_name = fn_elt.get_text()
        # Sometimes the "name" ends up being a repeat of the phone number, which is useless for us
        if not this_name or re.match(r'\+?[0-9]+', this_name):
            return this_number, None
    return this_number, this_name

main()
