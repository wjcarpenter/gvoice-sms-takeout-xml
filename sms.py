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
from operator import itemgetter
import pprint

__updated__ = "2023-12-02 14:23"

sms_backup_file  = None
call_backup_file = None
vm_backup_file   = None
chat_backup_file = None
takeout_voice_directory = os.path.join('Voice', 'Calls')
takeout_chat_directory = os.path.join('Google Chat', 'Groups')

# contacts dict by name
#   each value is a list
#     each item in the list is a timestamped_number: (phone number, timestamp)
#     for contacts read from the file, the timestamp is artificially sometime in the future
#       if the read contact already has a list of numbers, they are assumed to be in ascending order of preference
#     for discovered contacts, it's the timestamp of the message where we disovered the contact
#       if we discover the same contact again, we update the timestamp if it's later then the one we know
#     the head of the list is kept pointing at the timestamped_number with the latest timestamp
#
# phone number replacement policies:
#   as-is: take whatever number is in the file
#   latest: swap with the chronologically latest number we know
#   selective: swap as configured
#   acceptable: listed numbers as-is, all others swapped with preferred


contacts_oracle = None

# this is for some internal bookkeeping; you don't need to do anything with it.
missing_contacts = set()
conflicting_contacts = dict()

# some global counters for a stats summary at the end
counters = {
    'number_of_voice_sms_output':    0, 
    'number_of_chat_sms_output':     0, 
    'number_of_calls_output':        0, 
    "number_of_vms_output":          0,
    "conflict_warnings":             0,
    "todo_errors":                   0,
    "number_of_discovered_contacts": 0,
    }

# I really don't like globals, but there are just too many things to tote around in all these function calls.
phone_number_from_filename = None
contact_name_from_filename = None
phone_number_from_html_title = None
contact_name_from_html_title = None
html_elt = None

# This number is used a couple of places where we can't figure out the real number.
# If you want to manually fix things up, you should be able to easily search for it in
# either the inputs or the outputs.
BOGUS_NUMBER = "0000000000"

ATTACHMENT_TYPE_IMAGE = "image"
ATTACHMENT_TYPE_AUDIO = "audio"
ATTACHMENT_TYPE_VCARD = "vcard"

POLICY_ASIS = "asis"
POLICY_NEWEST = "newest"
POLICY_CONFIGURED = "configured"
# My convention is to use a relative filename when emitting into the XML
# and an absolute filename when printing a message for the person running the script.

def main():
    global sms_backup_file, vm_backup_file, call_backup_file, chat_backup_file
    global contacts_oracle
    global html_elt
    
    # This file is *optional* unless you get an error message asking you to add entries to it.
    contacts_filename = os.path.join('..', 'contacts.json')
    # SMS Backup and Restore likes to notice filenames that start with "sms-" or "calls-".
    # Save them to the parent directory so they are not lost if the Tajkeout file is
    # redone. The parent directory is the one that contains "Takeout". The script
    # expects to be run from within the "Takeout" directory by default.
    sms_backup_filename  = os.path.join('..', 'sms-gvoice.xml')
    call_backup_filename = os.path.join('..', 'calls-gvoice.xml')
    vm_backup_filename   = os.path.join('..', 'sms-vm-gvoice.xml')
    chat_backup_filename = os.path.join('..', 'sms-chat.xml')
    number_policy = POLICY_ASIS
    dump_data = False

    description = f'Convert Google Takeout HTML and Google Chat JSON files to SMS Backup and Restore XML files. (Version {__updated__})'
    epilog = ('All command line arguments are optional and have reasonable defaults when the script is run from within "Takeout/". '
        'The contacts file is optional. '
        'Output files should be named "sms-SOMETHING.xml" or "calls-SOMETHING.xml". '
        "See the README at https://github.com/wjcarpenter/gvoice-sms-takeout-xml for more information.")
    argparser = argparse.ArgumentParser(description=description, epilog=epilog)

    argparser.add_argument('-d', '--voice_directory',            
                           default="Voice/Calls",                  
                           help=f"The voice_directory containing the HTML files from Google Voice. Defaults to \"{takeout_voice_directory}\".")
    argparser.add_argument('-e', '--chat_directory',            
                           default="Google Chat/Groups",                  
                           help=f"The chat_directory containing the JSON files from Google Chat. Defaults to \"{takeout_chat_directory}\".")

    argparser.add_argument('-s', '--sms_backup_filename',  
                           default=sms_backup_filename,  
                           help=f"File to receive SMS/MMS messages from Google Voice. Defaults to \"{sms_backup_filename}\".")
    argparser.add_argument('-v', '--vm_backup_filename',   
                           default=vm_backup_filename,   
                           help=f"File to receive voicemail MMS messages from Google Voice. Defaults to \"{vm_backup_filename}\".")
    argparser.add_argument('-c', '--call_backup_filename', 
                           default=call_backup_filename, 
                           help=f"File to receive call history records from Google Voice. Defaults to \"{call_backup_filename}\".")
    argparser.add_argument('-t', '--chat_backup_filename', 
                           default=chat_backup_filename, 
                           help=f"File to receive SMS/MMS messages from Google Chat. Defaults to \"{chat_backup_filename}\".")

    argparser.add_argument('-j', '--contacts_filename',    
                           default=contacts_filename,    
                           help=f"JSON formatted file of definitive contact name/number pairs. Defaults to \"{contacts_filename}\".")
    argparser.add_argument('-p', '--number_policy',    
                           default=number_policy,
                           choices=(POLICY_ASIS, POLICY_CONFIGURED, POLICY_NEWEST),    
                           help=f"Policy for choosing the \"best\" number for a contact. Defaults to \"{number_policy}\".")
    argparser.add_argument('-z', '--dump_data',
                           action='store_true',
                           help=f"Dump some internal tables at the end of the run, which might help with sorting out some thing.")

    args = vars(argparser.parse_args())

    sms_backup_filename = args['sms_backup_filename']
    vm_backup_filename = args['vm_backup_filename']
    call_backup_filename = args['call_backup_filename']
    voice_directory = args['voice_directory']
    chat_directory = args['chat_directory']
    contacts_filename = args['contacts_filename']
    number_policy = args['number_policy']
    dump_data = args['dump_data']

    contacts_oracle = ContactsOracle(contacts_filename, number_policy)    
    prep_output_files(sms_backup_filename, vm_backup_filename, call_backup_filename, chat_backup_filename)
    
    print('>> 1st pass reading *.html files under', get_aka_path(voice_directory))
    # We make two passes over the HTML files. The first pass is merely to gather contact info so that
    # we have the complete picture before starting the second ("real") pass. That's so that we can
    # correctly apply phone number replacement policies for all of the HTML files. It's true that
    # some of the policies do not require this complete picture, and we could greatly reduce the files
    # processed in the second pass (maybe even not needing a second pass), but that clutters up the 
    # logic quite a bit. Since this is a one-time migration, efficiency is not that critical and we
    # accept the inefficiency for some number_policy cases.
    for subdirectory, __, files in os.walk(voice_directory):
        for html_basename in files:
            html_target = (subdirectory, html_basename)
            process_one_voice_file(True, html_target)

    with (open(sms_backup_filename,  'w') as sms_backup_file, 
          open(vm_backup_filename,   'w') as vm_backup_file, 
          open(call_backup_filename, 'w') as call_backup_file,
          open(chat_backup_filename, 'w') as chat_backup_file):
        
        write_dummy_headers()
        
        me_contact_number = contacts_oracle.get_number_by_name('Me', None)
        if not me_contact_number:
            print()
            print("Unfortunately, we can't figure out your own phone number.")
            print('TODO: Missing +phonenumber for contact: "Me": "+",')
            counters['todo_errors'] += 1
            missing_contacts.add('Me')
        else:
            print(f">> Your 'Me' phone number is {me_contact_number}")

        print('>> 2nd pass reading *.html files under', get_aka_path(voice_directory))
        # second pass over GV files
        for subdirectory, __, files in os.walk(voice_directory):
            for html_basename in files:
                html_target = (subdirectory, html_basename)
                process_one_voice_file(False, html_target)

        print('>> Reading chat files under', get_aka_path(voice_directory))
        for subdirectory, __, __ in os.walk(chat_directory):
            process_one_chat_file(subdirectory)

        write_trailers()
    
    # we have to reopen the files with a different mode for this
    write_real_headers(sms_backup_filename, vm_backup_filename, call_backup_filename, chat_backup_filename)
    print_counters(contacts_filename, sms_backup_filename, vm_backup_filename, call_backup_filename, chat_backup_filename)
    if dump_data:
        contacts_oracle.dump()

def process_one_chat_file(subdirectory):
    #participants = process_chat_group_info(subdirectory)
    #process_chat_messages(subdirectory, participants)
    pass

def process_one_voice_file(is_first_pass, html_target):
    global html_elt
    __, html_basename = html_target
    if not html_basename.endswith('.html'): return

    get_name_or_number_from_filename(html_basename)
    with open(get_rel_path(html_target), 'r', encoding="utf-8") as html_file:
        html_elt = BeautifulSoup(html_file, 'html.parser')
    get_name_or_number_from_title()

    if is_first_pass:
        scan_vcards_for_contacts(html_target, html_elt.body)
        return

    # Need to be firm about mapping contact names to numbers! The contact_name_to_number() function will complain.
    if contact_name_from_html_title and not contact_name_to_number(html_target, contact_name_from_html_title):
        return
    if contact_name_from_filename and not contact_name_to_number(html_target, contact_name_from_filename):
        return

    tags_div = html_elt.body.find(class_='tags')
    tag_elts = tags_div.find_all(rel='tag')
    tag_values = set()
    for tag_elt in tag_elts:
        tag_value = tag_elt.get_text()
        tag_values.add(tag_value)

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
        print(f"TODO: We can't figure out the contact name or number from an HTML file. Using '{BOGUS_NUMBER}'.")
        print(f'      due to File: "{get_abs_path(html_target)}"')
        return BOGUS_NUMBER
    contact_number = contacts_oracle.get_number_by_name(contact_name, None)
    if not contact_number and not contact_name in missing_contacts:
        print()
        print(f'TODO: Missing or disallowed +phonenumber for contact: "{contact_name}": "+",')
        print(f'      due to File: "{get_abs_path(html_target)}"')
        counters['todo_errors'] += 1
        # we add this fake entry to a dictionary so we don't keep complaining about the same thing
        missing_contacts.add(contact_name)
    return contact_number

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
        counters['number_of_voice_sms_output'] += 1

def write_mms_message_for_vm(html_target):
    # We want to end up with an MMS messages, just like any other, but the HTML input file is 
    # significantly different, so we have this bit of voodoo where we fake up some of the stuff.
    sender = None
    sender_name = None
    body_elt = html_elt.find('body')
    contributor_elt = body_elt.find(class_='contributor')
    this_number, this_name = get_number_and_name_from_tel_elt_parent(contributor_elt)
    if this_number:
        sender = contacts_oracle.get_best_number(this_number)
        sender_name = this_name
    if not sender:
        sender = get_sender_number_from_title_or_filename(html_target)
    if not sender_name:
        names = contacts_oracle.get_names_by_number(sender)
        if names:
            for sender_name in names:
                break

    participants = [sender] if sender else [BOGUS_NUMBER]
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
        counters['number_of_voice_sms_output'] += 1

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
    me_contact = contacts_oracle.get_number_by_name('Me', None)
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
            raw_number = contact_name_to_number(get_sender_name_from_title_or_filename(html_target))
        phone_number = contacts_oracle.get_best_number(raw_number)
        if not phone_number:
            contact_names = contacts_oracle.get_names_by_number(raw_number)
            if contact_names:
                for contact_name in contact_names:
                    break
            else:
                contact_name = get_sender_name_from_title_or_filename(html_target)
            print()
            print(f'TODO: Missing or disallowed +phonenumber for contact: "{contact_name}": "{raw_number}",')
            print(f'      due to File: "{get_abs_path(html_target)}"')
            counters['todo_errors'] += 1
            phone_number = BOGUS_NUMBER
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
        print()
        if raw_number:
            print(f"TODO: Possibly malformed contact phone number '{raw_number}' in HTML file. Using it anyhow.")
        else:
            print(f"TODO: Missing contact phone number in HTML file. Using '{BOGUS_NUMBER}'.")
        print(f'      due to File: "{get_abs_path(html_target)}"')
        counters['todo_errors'] += 1
        return raw_number
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

def is_phone_number(value):
    match_phone_number = re.match(r'(\+?[0-9]+)', value)
    if match_phone_number:
        return match_phone_number.group(1)
    return None 

def get_time_unix(message):
    time_elt = message.find(class_='dt')
    if not time_elt:
        time_elt = message.find(class_='published')
    iso_time = time_elt['title']
    parsed_iso_time = dateutil.parser.isoparse(iso_time);
    utc_offset_millis = parsed_iso_time.utcoffset().total_seconds() * 1000
    # timegm() doesn't take the TZ into account, so we have to adjust it manually
    timegm_millis = timegm(parsed_iso_time.timetuple()) * 1000
    unix_epoch_time_millis = timegm_millis - utc_offset_millis
    return int(unix_epoch_time_millis)

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

XML_HEADER = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n"
def write_dummy_headers():
    # The extra padding on the "count" lines are so that we can write the real count later
    # without worrying about not having enough space. The extra whitespace at that
    # place in the XML file is not significant.
    sms_backup_file.write(XML_HEADER)
    sms_backup_file.write('<smses count="0">'
                           '                                          \n')
    sms_backup_file.write("<!--Converted from Google Voice Takeout data -->\n")

    ################
    vm_backup_file.write(XML_HEADER)
    vm_backup_file.write('<smses count="0">'
                           '                                          \n')
    vm_backup_file.write("<!--Converted from Google Voice Takeout data -->\n")

    ################
    call_backup_file.write(XML_HEADER)
    call_backup_file.write('<calls count="0">'
                           '                                          \n')
    call_backup_file.write("<!--Converted from Google Voice Takeout data -->\n")

    ################
    chat_backup_file.write(XML_HEADER)
    chat_backup_file.write('<smses count="0">'
                           '                                          \n')
    chat_backup_file.write("<!--Converted from Google Chat Takeout data -->\n")

def print_counters(contacts_filename, sms_backup_filename, vm_backup_filename, call_backup_filename, chat_backup_filename):
    pp = pprint.PrettyPrinter(indent=2, width=100)
    print(">> Counters:")
    print(f">> {counters['number_of_voice_sms_output']:6} SMS/MMS records from Google Voice written to {get_aka_path(sms_backup_filename)}")
    print(f">> {counters['number_of_vms_output']:6} Voicemail records from Google Voice written to {get_aka_path(vm_backup_filename)}")
    print(f">> {counters['number_of_calls_output']:6} Call records from Google Voice written to {get_aka_path(call_backup_filename)}")
    print(f">> {counters['number_of_chat_sms_output']:6} SMS/MMS records from Google Chat written to {get_aka_path(chat_backup_filename)}")
    print(f">> {counters['number_of_discovered_contacts']:6} Contacts discovered in HTML files")
    print(f">> {counters['conflict_warnings']:6} Conflict info warnings given")
    print(f">> {counters['todo_errors']:6} TODO errors given")
    if counters['conflict_warnings'] > 0:
        print(">> Recap of conflict info warnings:")
        for name, numbers in conflicting_contacts.items():
            if len(numbers) > 1:
                print(f">>    {name}: {numbers}")
    if missing_contacts:
        print(">> Recap of missing or unresolved contacts (not including disallowed numbers):")
        print(f">>    {missing_contacts}")
        
#    print("Winter", contacts_oracle.get_number_by_name("Mike Winter", None))
#    print("Dang", contacts_oracle.get_number_by_name("Quynh Dang", None))
#    print("None", contacts_oracle.get_number_by_name("Nobody", None))
#    print("111111111", contacts_oracle.get_names_by_number("111111111"))
#    print("22222222", contacts_oracle.get_names_by_number("22222222"))
#    print("+17148123062", contacts_oracle.get_names_by_number("+17148123062"))
    print(">> Me", contacts_oracle.get_number_by_name("Me", None))
    print(">> Me", contacts_oracle.get_number_by_name("The Other Me", None))
    print(">> Me", contacts_oracle.get_number_by_name("Aliased Me", None))
    
def write_real_headers(sms_backup_filename, vm_backup_filename, call_backup_filename, chat_backup_filename):
    print()

    with open(sms_backup_filename, 'r+') as backup_file:
        backup_file.write(XML_HEADER)
        backup_file.write(f'<smses count="{counters["number_of_voice_sms_output"]}">\n')

    ################
    with open(vm_backup_filename, 'r+') as backup_file:
        backup_file.write(XML_HEADER)
        backup_file.write(f'<smses count="{counters["number_of_vms_output"]}">\n')

    ################
    with open(call_backup_filename, 'r+') as backup_file:
        backup_file.write(XML_HEADER)
        backup_file.write(f'<calls count="{counters["number_of_calls_output"]}">\n')

    ################
    with open(chat_backup_filename, 'r+') as backup_file:
        backup_file.write(XML_HEADER)
        backup_file.write(f'<smses count="{counters["number_of_chat_sms_output"]}">\n')


def write_trailers():
    sms_backup_file.write('</smses>\n')
    vm_backup_file.write('</smses>\n')
    call_backup_file.write('</calls>\n')
    chat_backup_file.write('</smses>\n')

def prep_output_files(sms_backup_filename, vm_backup_filename, call_backup_filename, chat_backup_filename):
    sms_backup_filename_BAK = sms_backup_filename + '.BAK'
    if os.path.exists(sms_backup_filename):
        if os.path.exists(sms_backup_filename_BAK):
            print('>> Removing', os.path.abspath(sms_backup_filename_BAK))
            os.remove(sms_backup_filename_BAK)
        print('>> Renaming existing SMS/MMS output file to', os.path.abspath(sms_backup_filename_BAK))
        os.rename(sms_backup_filename, sms_backup_filename_BAK)

    print('>> SMS/MMS from Google Voice will be written to',  get_aka_path(sms_backup_filename))
    print(">>")

    call_backup_filename_BAK = call_backup_filename + '.BAK'
    if os.path.exists(call_backup_filename):
        if os.path.exists(call_backup_filename_BAK):
            print('>> Removing', os.path.abspath(call_backup_filename_BAK))
            os.remove(call_backup_filename_BAK)
        print('>> Renaming existing Calls output file to', os.path.abspath(call_backup_filename_BAK))
        os.rename(call_backup_filename, call_backup_filename_BAK)

    print('>> Call history from Google Voice will be written to', get_aka_path(call_backup_filename))
    print(">>")

    vm_backup_filename_BAK = vm_backup_filename + '.BAK'
    if os.path.exists(vm_backup_filename):
        if os.path.exists(vm_backup_filename_BAK):
            print('>> Removing', os.path.abspath(vm_backup_filename_BAK))
            os.remove(vm_backup_filename_BAK)
        print('>> Renaming existing Voicemail output file to', os.path.abspath(vm_backup_filename_BAK))
        os.rename(vm_backup_filename, vm_backup_filename_BAK)

    print('>> Voicemail MMS from Google Voice will be written to', get_aka_path(vm_backup_filename))
    print(">>")

    chat_backup_filename_BAK = chat_backup_filename + '.BAK'
    if os.path.exists(chat_backup_filename):
        if os.path.exists(chat_backup_filename_BAK):
            print('>> Removing', os.path.abspath(chat_backup_filename_BAK))
            os.remove(chat_backup_filename_BAK)
        print('>> Renaming existing SMS/MMS output file to', os.path.abspath(chat_backup_filename_BAK))
        os.rename(chat_backup_filename, chat_backup_filename_BAK)

    print('>> SMS/MMS from Google Chat will be written to', get_aka_path(chat_backup_filename))
    print(">>")

    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

# In some extreme cases, we have to pick our the correspondent from the name
# of the file. It can be a phone number or a contact name, or it can be completely missing.
def get_name_or_number_from_filename(html_basename):
    global phone_number_from_filename, contact_name_from_filename
    contact_name_from_filename = None
    phone_number_from_filename = is_phone_number(html_basename)
    if not phone_number_from_filename:
        # sometimes a single " - ", sometimes two of them
        match_name = re.match(r'([^ ].*) - .+ - ', html_basename)
        if not match_name:
            match_name = re.match(r'([^ ].*) - ', html_basename)
        if match_name:
            contact_name_from_filename = match_name.group(1)
            if contact_name_from_filename == "Group Conversation":
                contact_name_from_filename = None
    return (contact_name_from_filename, phone_number_from_filename)


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
        return (None, None)

    match_phone_number = is_phone_number(correspondent)
    if match_phone_number:
        # I think this doesn't actually happen
        phone_number_from_html_title = match_phone_number.group(1)
    else:
        contact_name_from_html_title = correspondent
        if contact_name_from_html_title == "Group Conversation":
            contact_name_from_html_title = None
    return (contact_name_from_html_title, phone_number_from_html_title)

# Iterate all of the vcards in the HTML body to speculatively populate the
# contacts list. Also make a note of a contact which is "not me" for
# use as the address in an SMS record (it's always "the other end"). The
# same logic does not apply to MMS, which has a different scheme for address.
def scan_vcards_for_contacts(html_target, parent_elt):
    global me
    not_me_vcard_number = None
    # We make the simplifying assumption that the timestamps in any given HTML file
    # are close (enough) together and it doesn't matter much which one we use for
    # the contact timestamp. 
    timestamp = get_time_unix(parent_elt)
    
    vcard_elts = parent_elt.find_all(class_="vcard")
    for vcard_elt in vcard_elts:
        this_number, this_name = get_number_and_name_from_tel_elt_parent(vcard_elt)
        if this_number:
            if this_name != "Me":
                not_me_vcard_number = this_number
            if this_name:
                number_is_known = contacts_oracle.is_already_known_pair(this_name, this_number)
                if contacts_oracle.add_discovered_contact(this_name, this_number, timestamp):
                    counters['number_of_discovered_contacts'] += 1
                if not number_is_known:
                    conflict_list = conflicting_contacts.get(this_name, None)
                    if not conflict_list:
                        conflict_list = list()
                        conflict_list.append(this_number)
                    if not this_number in conflict_list:
                        print(f'>> Info: conflicting information about "{this_name}":', conflict_list, f"'{this_number}'")
                        print(f'>>    due to File: "{get_abs_path(html_target)}"')
                        counters['conflict_warnings'] += 1
                        conflict_list.append(this_number)
                    conflicting_contacts[this_name] = conflict_list
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
        if not this_name or is_phone_number(this_name):
            return this_number, None
    return this_number, this_name

# The (optional) contacts file can have these types of entries:
# 1. some name: some other name          (this is a simple aliasing scheme for contact names)
# 2. some name: some number              (a degenerate case that is turned into a list)
# 3. some name: [some list of numbers]   (all of these numbers are acceptable for this contact name; leftmost is preferred)
# 4. some number: some other number      (if some number is seen, some other number will be used in output)
class ContactsOracle:
    def __init__(self, contacts_filename, policy):
        self._contacts_filename = contacts_filename
        self._name_to_name = dict()
        self._number_to_number = dict()
        self._name_to_numbers = dict()
        self._number_to_names = dict()
        self._policy = policy
        
        if not os.path.exists(self._contacts_filename):
            print('>> No (optional) JSON contacts file', os.path.abspath(self._contacts_filename))
            return
        
        print('>> Reading contacts from JSON contacts file', os.path.abspath(self._contacts_filename))
        with open(self._contacts_filename) as cnf: 
            cn_data = cnf.read() 
        parsed_file = json.loads(cn_data)
        for key, value in parsed_file.items():
            key_is_name = not is_phone_number(key)
            if key_is_name:
                self._do_name_entry(key, value)
            else:
                self._do_number_entry(key, value)

        print(">> JSON contact configuration counts:")
        print(f'>> {len(self._name_to_numbers):6} Name-to-number(s) entries')
        print(f'>> {len(self._name_to_name):6} Name-to-name entries')
        print(f'>> {len(self._number_to_number):6} Number-to-number entries')
        print(f'>> {len(self._number_to_names):6} Number-to-names entries (computed)')
        print(f">> Contact phone number replacement policy is '{self._policy}'")

    def _do_name_entry(self, name, value):
        if isinstance(value, str):
            if not is_phone_number(value):
                # not mapping to a number, so must be an alias
                self._name_to_name[name] = value
                return
            values = [value]  # simple scalar; make it a list
        elif isinstance(value, list):
            values = value
        else:
            raise Exception(f'"{name}" entry value of type {type(value)} is not a string or a list: {value}\n    in {get_aka_path(self._contacts_filename)}')

        far_future = 5_000_000_000_000  # a pseudo-Unix timestamp, in ms, in the distant future
        for ii in range(len(values)):
            value = values[ii]
            if not is_phone_number(value):
                raise Exception(f'"{name}" entry value of type {type(value)} is not a phone number: {value}\n    in {get_aka_path(self._contacts_filename)}')
            # (value, timestamp, isconfigured)
            timestamped_number = (value, far_future - ii, True)
            values[ii] = timestamped_number
            self._add_number_to_name_item(name, value)
        # these are already reverse sorted; just belt and suspenders
        values.sort(key=itemgetter(1), reverse=True)
        self._name_to_numbers[name] = values
        
    def _add_number_to_name_item(self, name, number):
        existing = self._number_to_names.get(number, None)
        if not existing:
            existing = set()
            self._number_to_names[number] = existing
        existing.add(name)  # it's a set, so we don't care if it's duplicate
        
    def _do_number_entry(self, number, name):
        if not isinstance(name, str) or not is_phone_number(name):
            raise Exception(f'"{number}" entry value of type {type(name)} is not a phone number: {name}\n    in {get_aka_path(self._contacts_filename)}')
        self._number_to_number[name] = number
        
    def is_already_known_pair(self, name, number):
        if not name or not number:
            return False
        existing_list = self._name_to_numbers.get(name, None)
        if not existing_list:
            alias_to = self._name_to_name.get(name, None)
            return self.is_already_known_pair(alias_to, number)
        for this_number, __, __ in existing_list:
            if this_number == number:
                return True
        return False
        
    # This is really inefficient, but we're banking on the set of contacts being managable
    def add_discovered_contact(self, name, number, timestamp):
        # We could ignore any discovered contacts for policy "configured", but we want to 
        # do proper countihg and give messages to the user, etc.
        if is_phone_number(name):
            # it's a number that pairs with itself instead of a name, so ignore it.
            return False
        existing_list = self._name_to_numbers.get(name, None)
        if not existing_list:
            existing_list = list()
            self._name_to_numbers[name] = existing_list
        found_it = False
        # (value, timestamp, isconfigured)
        new_tuple = (number, timestamp, False)
        for ii in range(len(existing_list)):
            this_tuple = existing_list[ii]
            this_number, this_timestamp, this_isconfigured = this_tuple
            if this_number == number:
                found_it = True
                if timestamp > this_timestamp:
                    # it's a newer discovery
                    # we only want to update discovered items, but the timestamps of the configured items 
                    # will already deal with that because configured timestamps are artificially far future
                    existing_list[ii] = new_tuple
                break

        if not found_it:
            existing_list.append(new_tuple)
            self._add_number_to_name_item(name, number)
            
        existing_list.sort(key=itemgetter(1), reverse=True)
        
        return not found_it

    # The strategy for this method and the next is to first do a lookup by the 
    # passed in key. If that doesn't yield a result, see if the key is an 
    # alias and try again with the pointed-to key. We'll eventually get a hit
    # or reach the end of the chain.
    # The argument "number" is typically None, but if it does have a value
    # we'll see if we can do better, where "better" is according to policy.
    def get_number_by_name(self, name, number):
        if not name:                            return number  # only happens by recursion
        elif self._policy == POLICY_ASIS:       return self._policy_asis(name, number)
        elif self._policy == POLICY_CONFIGURED: return self._policy_configured(name, number)
        elif self._policy == POLICY_NEWEST:     return self._policy_newest(name)
        else:
            raise Exception(f'We don''t recognize this number policy: "{self._policy}". It''s probably a bug in the script.')
    
    def _policy_asis(self, name, number):
        if number:
            return number
        else:
            try:
                self._policy = POLICY_NEWEST
                return self.get_number_by_name(name, number)
            finally:
                self._policy = POLICY_ASIS                    
        
    def _policy_newest(self, name):
        candidate_list = self._name_to_numbers.get(name, None)
        if candidate_list:
            # candidate_list will be a list with the first item the preferred number
            this_number, this_timestamp, this_isconfigured = candidate_list[0]
            return this_number
        else:
            aliased_to = self._name_to_name.get(name, None)
            return self.get_number_by_name(aliased_to, None)
        
    def _policy_configured(self, name, number):
        value = None
        candidate_list = self._name_to_numbers.get(name, None)
        if candidate_list:
            # if no candidate number was passed in, return the best configured number
            if not number:
                this_number, this_timestamp, this_isconfigured = candidate_list[0]
                if this_isconfigured:
                    value = this_number
            else:
                # a number was passed in, so vet it
                for this_number, this_timestamp, this_isconfigured in candidate_list:
                    if this_isconfigured and number == this_number:
                        value = this_number
                        break
    
        if value:
            return value
        else:
            aliased_to = self._name_to_name.get(name, None)
            return self.get_number_by_name(aliased_to, None)

    def get_names_by_number(self, number):
        if not number:
            return None
        value = self._number_to_names.get(number, None)
        if value:
            return value

        return self.get_names_by_number(self._number_to_number.get(number, None))

    def get_best_number(self, number):
        if self._policy == POLICY_ASIS:
            return number
        best_timestamp = 0
        best_number = None
        names = self.get_names_by_number(number)
        if names:
            for name in names:
                # iterate overa all the names, choosing the latest timestamp from among all of them
                tuples = self._name_to_numbers.get(name, None)
                if tuples:
                    this_number, this_timestamp, this_isconfigured = tuples[0]
                    if self._policy == POLICY_CONFIGURED and not this_isconfigured:
                        continue
                    if this_timestamp > best_timestamp:
                        best_timestamp = this_timestamp
                        best_number = this_number
            if best_number:
                return best_number
        else:
            return number
        
    def dump(self):
        pp = pprint.PrettyPrinter(indent=2, width=100)
        print()
        print("Mappings of names-to-numbers (configured and discovered):")
        pp.pprint(self._name_to_numbers)
        print()
        print("Mappings of numbers-to-names (computed reverse mappings)")
        pp.pprint(self._number_to_names)
        print()
        print("Mappings of names-to-names (configured name aliases):")
        pp.pprint(self._name_to_name)
        print()
        print("Mappings of numbers-to-numbers (configured number aliases):")
        pp.pprint(self._number_to_number)

main()

