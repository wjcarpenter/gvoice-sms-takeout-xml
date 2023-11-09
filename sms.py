from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings
warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)
from bs4.formatter import XMLFormatter, Formatter, HTMLFormatter
from bs4.element import Comment
from bs4.dammit import EntitySubstitution
import re
import os
import phonenumbers
import dateutil.parser
import datetime
from calendar import timegm
import base64
from io import open # adds emoji support
import json
import isodate

# SMS Backup and Restore likes to notice filename that start with "sms-"
# Save it to the great-grandparent directory because it can otherwise be hard to find amongst
# the zillion HTML files. The great-grandparent directory is the one that contains
# "Takeout" as a subdirectory, and you should run this script from the
# Takeout/Voice/Calls subdirectory.

sms_backup_filename  = "../../../sms-gvoice-all.xml"
call_backup_filename = "../../../calls-gvoice-all.xml"
vm_backup_filename   = "../../../sms-vm-gvoice-all.xml"

# We sometimes see isolated messages from ourselves to someone, and the Takeout format
# only identifies them by contact name instead of phone number. In such cases, we
# consult this optional JSON file to map  the name to a phone number (which should
# include the "+" and country code and no other punctuation). Must be valid JSON, eg:
# {
#   "me": "+441234567890",
#   "Joe Blow": "+18885551234",
#   "Susie Glow": "+18885554321"
# }
# In cases where there is no JSON entry when needed, a warning is printed. Update
# the JSON file and re-run this script. Don't try to restore with the output
# file until you have resolved all of those contacts warnings.

# This file is *optional*
contact_number_file = "../../../contacts.json"
# The contacts JSON file, if present, is read into this dictionary, but discovered entries are also read into it.
contacts = dict()

# this is for some internal bookkeeping; you don't need to do anything with it.
missing_contacts = set()
conflicting_contacts = set()
me = None

# some global counters
num_sms = 0
num_calls = 0
num_vms = 0

# I really don't like globals, but there are just too many things to tote around in all these function calls.
subdir = None
# The convention is to use a relative filename when emitting into the XML
# and an absolute filename when printing a message for the person running the script.
html_filename_basename = None
html_filename_rel_path = None
html_filename_abs_path = None
phone_number_from_filename = None
contact_name_from_filename = None
phone_number_from_html_title = None
contact_name_from_html_title = None
html_elt = None

def main():
    global html_filename_basename, html_filename_rel_path, html_filename_abs_path, subdir
    global html_elt
    prep_output_files()
    print('>> Reading *.html files under', os.getcwd())
    come_back_later = []
    write_dummy_headers()

    for subdir, dirs, files in os.walk("."):
        for html_filename_basename in files:
            process_one_file(True, come_back_later)

    if not me and come_back_later:
        print()
        print("Unfortunately, we can't figure out your own phone number.")
        print(os.path.abspath(contact_number_file) + ': TODO: add a +phonenumber for contact: "me": "+",')
    else:
        print(">> Your 'me' phone number is", me)
        for subdir, html_filename_basename in come_back_later:
            process_one_file(False, come_back_later)

    sms_backup_file = open(sms_backup_filename, 'a'); sms_backup_file.write(u'</smses>\n'); sms_backup_file.close()
    vm_backup_file = open(vm_backup_filename, 'a'); vm_backup_file.write(u'</smses>\n'); vm_backup_file.close()
    call_backup_file = open(call_backup_filename, 'a'); call_backup_file.write(u'</calls>\n'); call_backup_file.close()
    write_real_headers()

def process_one_file(first_pass, come_back_later):
    global html_filename_rel_path, html_filename_abs_path
    global html_elt
    html_filename_rel_path = os.path.join(subdir, html_filename_basename)
    html_file = open(html_filename_rel_path, 'r', encoding="utf-8")

    if not html_filename_basename.endswith('.html'): return
    get_name_or_number_from_filename()
    html_filename_abs_path = os.path.abspath(html_filename_rel_path)
    html_elt = BeautifulSoup(html_file, 'html.parser')
    get_name_or_number_from_title()

    tags_div = html_elt.body.find(class_='tags')
    tag_elts = tags_div.find_all(rel='tag')
    tag_values = set()
    for tag_elt in tag_elts:
        tag_value = tag_elt.get_text()
        tag_values.add(tag_value)

    scan_vcards_for_contacts(html_elt.body)
    need_title_contact = contact_name_from_html_title and not contacts.get(contact_name_from_html_title, None)
    need_filename_contact = contact_name_from_filename and not contacts.get(contact_name_from_filename, None)
    if first_pass and (not me or need_title_contact or need_filename_contact):
        if "Text" in tag_values or "Voicemail" in tag_values or "Recorded" in tag_values:
            # Can't do anything rational for SMS/MMS if we don't know our own number.
            # We _might_ be able to get along without the phone numbers for the contacts
            # named in the filename or the HTML title, but not always. Save them for
            # the second pass just in case.
            print(">> Deferring:", html_filename_abs_path)
            come_back_later.append([subdir, html_filename_basename])
            return

    if not first_pass:
        print(">> 2nd  pass:", html_filename_abs_path)
        # need to be firmer about mapping contact names to numbers!
        if contact_name_from_html_title and not contact_name_to_number(contact_name_from_html_title):
            return
        if contact_name_from_filename and not contact_name_to_number(contact_name_from_filename):
            return

    if   "Text"      in tag_values:  process_Text()
    elif "Received"  in tag_values:  process_call(1)
    elif "Placed"    in tag_values:  process_call(2)
    elif "Missed"    in tag_values:  process_call(3)
    elif "Voicemail" in tag_values:  process_Voicemail()
    elif "Recorded"  in tag_values:  process_Voicemail()
    else:
        print("Unrecognized tag_value situation '" + str(tag_values) + "'; silently ignoring file '" + html_filename_rel_path + "'")

def process_Text():
    # This can be either SMS or MMS. MMS can be either with or without attachments.
    message_elts = html_elt.find_all(class_='message')
    participants_elt = html_elt.find(class_='participants')

    if participants_elt:
        write_mms_messages(participants_elt, message_elts)
    else:
        write_sms_messages(message_elts)

def process_Voicemail():
    process_call(4)
    body = html_elt.find('body')
    write_mms_message_for_vm(body)

def process_call(call_type):
    contributor = html_elt.body.find(class_="contributor")
    telephone_number_elt = contributor.find(class_="tel")
    telephone_number_full = telephone_number_elt.attrs['href']
    telephone_number_suffix = telephone_number_full[4:]
    if telephone_number_suffix == '':
        presentation = '2'
        telephone_number = telephone_number_suffix
    else:
        presentation = '1'
        try:
            telephone_number = format_number(phonenumbers.parse(telephone_number_suffix, None))
        except phonenumbers.phonenumberutil.NumberParseException:
            # I also saw this on a 10-year-old "Placed" call. Probably a data glitch.
            telephone_number = telephone_number_suffix

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
    write_call_message(telephone_number, presentation, duration, timestamp, call_type, readable_date)

def contact_name_to_number(contact_name):
    if not contact_name:
        print(f'File: "{html_filename_abs_path}"')
        print("We can't figure out the name or number for a contact in the above file.")
        return "0"
    contact_number = contacts.get(contact_name, None)
    if not contact_number and not contact_name in missing_contacts:
        print()
        print(f'TODO: {os.path.abspath(contact_number_file)}: add a +phonenumber for contact: "{contact_name}": "+",')
        print(f'      due to File: "{html_filename_abs_path}"')
        # we add this fake entry to a dictionary so we don't keep complaining about the same thing
        missing_contacts.add(contact_name)
    return contact_number

def contact_number_to_name(contact_number):
    if contact_number:
        for name, number in contacts.items():
            if number == contact_number:
                return name
    return None

def get_sender_number_from_title_or_filename():
    if phone_number_from_html_title:
        sender = phone_number_from_html_title
    elif contact_name_from_html_title:
        sender = contact_name_to_number(contact_name_from_html_title)
    elif phone_number_from_filename:
        sender = phone_number_from_filename
    elif contact_name_from_filename:
        sender = contact_name_to_number(contact_name_from_filename)
    else:
        sender = None
    return sender

def write_call_message(telephone_number, presentation, duration, timestamp, call_type, readable_date):
    global num_calls
    call_backup_file = open(call_backup_filename, 'a')
    parent_elt = BeautifulSoup()
    file_comment = Comment(f'file: "{html_filename_rel_path}"')
    parent_elt.append(file_comment)
    bs4_append_call_elt(parent_elt, telephone_number, duration, timestamp, presentation, readable_date, call_type)
    call_backup_file.write(parent_elt.prettify())
    call_backup_file.write('\n')
    call_backup_file.close()
    num_calls += 1

def write_sms_messages(message_elts):
    global num_sms, num_vms, num_calls
    other_party_number = None
    # Since the "address" element of an SMS is always the other end, scan the
    # message elements until we find a number this not "me". Use that as the
    # address value for all of the SMS files in this HTML.
    for i in range(len(message_elts)):
        message_elt = message_elts[i]
        if other_party_number is None:
            other_party_number = scan_vcards_for_contacts(message_elt)
            if other_party_number is not None:
                break
    # This will be the case if the HTML file contains only a single SMS
    # that was sent by "me". Use fallbacks.
    if other_party_number is None:
        other_party_number = get_sender_number_from_title_or_filename()

    backup_file = open(sms_backup_filename, 'a')

    for i in range(len(message_elts)):
        message_elt = message_elts[i]
        the_text = get_message_text(message_elt)
        message_type = get_message_type(message_elt)
        sent_by_me = (message_type == 2)
        timestamp = get_time_unix(message_elt)
        attachments = get_attachment_elts(message_elt)
        parent_elt = BeautifulSoup()
        file_comment = Comment(f'file: "{html_filename_rel_path}"')
        parent_elt.append(file_comment)
        # if it was just an image with no text, there is no point in creating an empty SMS to go with it
        if the_text and the_text != "MMS Sent" and not attachments:
            bs4_append_sms_elt(parent_elt, other_party_number, timestamp, the_text, message_type)
        else:
            msgbox_type = message_type
            bs4_append_mms_elt_with_parts(parent_elt, attachments, the_text, other_party_number, sent_by_me, timestamp, msgbox_type, [other_party_number])
        backup_file.write(parent_elt.prettify())
        backup_file.write('\n')
        num_sms += 1

    backup_file.close()

def write_mms_message_for_vm(body):
    global num_sms, num_vms, num_calls
    sender = None
    sender_name = None
    contributor_elt = body.find(class_='contributor')
    this_number, this_name = get_number_and_name_from_tel_elt_parent(contributor_elt)
    if this_number:
        sender = this_number
        sender_name = this_name
    if not sender:
        sender = get_sender_number_from_title_or_filename()
    if not sender_name:
        sender_name = contact_number_to_name(sender)

    participants = [sender] if sender else ["0"]
    timestamp = get_time_unix(body)
    vm_from = (sender_name if sender_name else sender if sender else "Unknown")
    transcript = get_vm_transcript(body)
    if transcript:
        the_text = "Voicemail/Recording from: " + vm_from + "\nTranscript: " + transcript
    else:
        the_text = "Voicemail/Recording from: " + vm_from        
    attachment_elts = get_attachment_elts(body)
    msgbox_type = '1' # 1 = Received, 2 = Sent
    sent_by_me = False
    parent_elt = BeautifulSoup()
    file_comment = Comment(f'file: "{html_filename_rel_path}"')
    parent_elt.append(file_comment)
    bs4_append_mms_elt_with_parts(parent_elt, attachment_elts, the_text, sender, sent_by_me, timestamp, msgbox_type, participants)
    vms_backup_file = open(vm_backup_filename, "a")
    vms_backup_file.write(parent_elt.prettify())
    vms_backup_file.write('\n')
    vms_backup_file.close()
    num_vms += 1

def write_mms_messages(participants_elt, message_elts):
    global num_sms, num_vms, num_calls
    sms_backup_file = open(sms_backup_filename, 'a')

    participants = get_participant_phone_numbers(participants_elt)

    for i in range(len(message_elts)):
        message_elt = message_elts[i]
        # TODO who is sender?
        not_me_vcard_number = scan_vcards_for_contacts(message_elt)
        sender = not_me_vcard_number
        sent_by_me = sender not in participants
        the_text = get_message_text(message_elt)
        message_type = get_message_type(message_elt)
        timestamp = get_time_unix(message_elt)
        attachments = get_attachment_elts(message_elt)

        parent_elt = BeautifulSoup()
        file_comment = Comment(f'file: "{html_filename_rel_path}"')
        parent_elt.append(file_comment)
        bs4_append_mms_elt_with_parts(parent_elt, attachments, the_text, sender, sent_by_me, timestamp, None, participants)
        sms_backup_file.write(parent_elt.prettify())
        sms_backup_file.write('\n')
        num_sms += 1

    sms_backup_file.close()

def get_attachment_elts(message_elt):
    attachments = []
    div_elts = message_elt.find_all('div')
    for i in range(len(div_elts)):
        div_elt = div_elts[i]
        img_elt = div_elt.find('img')
        if img_elt:
            attachments.append(img_elt)
        audio_elt = div_elt.find('audio')
        if audio_elt:
            attachments.append(audio_elt)
        vcard_elt = div_elt.find(class_='vcard')
        if vcard_elt and vcard_elt.name == "a":
            attachments.append(vcard_elt)
    return attachments

def bs4_append_sms_elt(parent_elt, sender, timestamp, the_text, message_type):
    sms_elt = html_elt.new_tag('sms')
    parent_elt.append(sms_elt)

    sms_elt['protocol'] = '0'
    sms_elt['address'] = sender
    sms_elt['timestamp'] = timestamp
    sms_elt['type'] = message_type
    sms_elt['subject'] = 'null'
    sms_elt['body'] = the_text
    sms_elt['toa'] = 'null'
    sms_elt['sc_toa'] = 'null'
    sms_elt['service_center'] = 'null'
    sms_elt['read'] = '1'
    sms_elt['status'] = '1'
    sms_elt['locked'] = '0'

def bs4_append_mms_elt_with_parts(parent_elt, attachment_elts, the_text, sender, sent_by_me, timestamp, msgbox_type, participants):
    m_type = 128 if sent_by_me else 132
    bs4_append_mms_elt(parent_elt, participants, timestamp, m_type, msgbox_type, sender, sent_by_me, the_text)
    mms_elt = parent_elt.mms

    if attachment_elts:
        parts_elt = mms_elt.parts
        bs4_append_part_elts(parts_elt, attachment_elts)

def bs4_append_part_elts(parent_elt, attachment_elts):
    for i in range(len(attachment_elts)):
        attachment_elt = attachment_elts[i]
        sequence_number = i
        if attachment_elt.name == 'img':
            attachment_file_ref = attachment_elt['src']
            bs4_append_part_elt(parent_elt, "image", sequence_number, attachment_file_ref)
        elif attachment_elt.name == 'audio':
            attachment_file_ref = attachment_elt.a['href']
            bs4_append_part_elt(parent_elt, "audio", sequence_number, attachment_file_ref)
        elif attachment_elt.name == 'a' and 'vcard' in attachment_elt['class']:
            attachment_file_ref = attachment_elt['href']
            bs4_append_part_elt(parent_elt, "vcard", sequence_number, attachment_file_ref)
        else:
            print("Unrecognized MMS attachment in file", html_filename_abs_path, ":\n", attachment_elt)
    
def bs4_append_part_elt(parent_elt, attachment_type, sequence_number, attachment_file_ref):
    attachment_filename, content_type = figure_out_attachment_filename_and_type(attachment_type, attachment_file_ref)
    if attachment_filename:
        attachment_filename_rel_path = os.path.join(subdir, attachment_filename)
        attachment_file = open(attachment_filename, 'rb') 
        attachment_data = base64.b64encode(attachment_file.read()).decode()
        attachment_file.close()
        attachment_filename_rel_path = os.path.join(subdir, attachment_filename)
        file_comment = Comment(f'file: "{attachment_filename_rel_path}"')
        parent_elt.append(file_comment)
        #bs4_part_elt_parent(parent_elt, sequence_number, content_type, attachment_filename, attachment_data)
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

def bs4_append_mms_elt(parent_elt, participants, timestamp, m_type, msgbox_type, sender, sent_by_me, the_text):
    mms_elt = html_elt.new_tag('mms')
    parent_elt.append(mms_elt)

    bs4_append_addrs_elt(mms_elt, participants, sender, sent_by_me)

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
    # read_status - The read-status of the message.
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

def bs4_append_addrs_elt(elt_parent, participants, sender, sent_by_me):
    addrs_elt = html_elt.new_tag('addrs')
    elt_parent.append(addrs_elt)
    for participant in participants + [me]:
        participant_is_sender = ((participant == sender) or (sent_by_me and participant == me))
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
    call_elt['call_type'] = call_type    
    
    # subscription_id - Optional field that has the id of the phone subscription (SIM). On some phones these are values like 0, 1, 2  etc. based on how the phone assigns the index to the sim being used while others have the full SIM ID.
    # contact_name - Optional field that has the name of the contact.
    
    parent_elt.append(call_elt)

def figure_out_attachment_filename_and_type(attachment_type, attachment_file_ref):
    base, ext = os.path.splitext(attachment_file_ref)
    attachment_filename, content_type = consider_this_attachment_file_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    base = base[:50]  # this is odd; probably bugs in Takeout or at least weird choices
    attachment_filename, content_type = consider_this_attachment_file_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    base, ext = os.path.splitext(html_filename_basename)
    attachment_filename, content_type = consider_this_attachment_file_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type
        
    base = base[:50]  # this is odd; probably bugs in Takeout or at least weird choices
    attachment_filename, content_type = consider_this_attachment_file_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    print(attachment_type, "attachment referenced in message, but not found:", os.path.abspath(os.path.join(subdir, attachment_file_ref)))
    print("  src='" + attachment_file_ref + "'")
    print("  referenced from", html_filename_abs_path)
    return None, None
    
def consider_this_attachment_file_candidate(base, attachment_type):
    if attachment_type == "image":
        if os.path.exists(base + '.jpg'):
            attachment_filename = base + '.jpg'
            content_type = 'image/jpeg'
            return attachment_filename, content_type
        elif os.path.exists(base + '.gif'):
            attachment_filename = base + '.gif'
            content_type = 'image/gif'
            return attachment_filename, content_type
        elif os.path.exists(base + '.png'):
            attachment_filename = base + '.png'
            content_type = 'image/png'
            return attachment_filename, content_type
    elif attachment_type == "audio":
        if os.path.exists(base + '.mp3'):
            attachment_filename = base + '.mp3'
            content_type = 'audio/mp3'
            return attachment_filename, content_type
    elif attachment_type == "vcard":
        if os.path.exists(base + '.vcf'):
            attachment_filename = base + '.vcf'
            content_type = 'text/x-vCard'
            return attachment_filename, content_type
    return None, None
    
def get_message_type(message): # author_elt = message_elts[i].cite
    author_elt = message.cite
    if ( not author_elt.span ):
        return 2
    else:
        return 1

def get_vm_transcript(message_elt):
    full_text_elt = message_elt.find(class_='full-text')
    if not full_text_elt:
        return None
    
    return BeautifulSoup(full_text_elt.text,'html.parser').prettify().strip()

def get_message_text(message_elt):
    text_elt = message_elt.find('q')
    if not text_elt:
        return ""
    return BeautifulSoup(text_elt.text,'html.parser').prettify().strip()

def get_participant_phone_numbers(participant_elt):
    participants = []
    participant_elts = [participant_elt]
    for participant_set in participant_elts:
        for participant in participant_set:
            if (not hasattr(participant, 'a')):
                continue

            try:
                raw_number = participant.a['href'][4:]
                if not raw_number:
                    raw_number = contact_name_to_number(get_sender_number_from_title_or_filename())
                phone_number = phonenumbers.parse(raw_number, None)
            except phonenumbers.phonenumberutil.NumberParseException:
                participants.append(participant.a['href'][4:])

            participants.append(format_number(phone_number))

    if participants == []:
        if phone_number_from_html_title is None:
            phone_number_from_html_title = contact_name_to_number(contact_name_from_html_title)
        participants.append(contact_name_to_number(phone_number_from_html_title))
                
    return participants

def format_number(phone_number):
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

def get_time_unix(message):
    time_elt = message.find(class_='dt')
    if not time_elt:
        time_elt = message.find(class_='published')
    iso_time = time_elt['title']
    time_obj = dateutil.parser.isoparse(iso_time);
    mstime = timegm(time_obj.timetuple()) * 1000 + time_obj.microsecond / 1000
    return int(mstime)

xml_header = u"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n"
def write_dummy_headers():
    # The extra padding on the "count" lines are so that we can write the real count later
    # without worrying about not having enough space. The extra whitespace at that
    # place in the XML file is not significant.
    backup_file = open(sms_backup_filename, 'w')
    backup_file.write(xml_header)
    backup_file.write(u'<smses count="0">                                           \n')
    backup_file.write(u"<!--Converted from GV Takeout data -->\n")
    backup_file.close()

    ################
    backup_file = open(vm_backup_filename, 'w')
    backup_file.write(xml_header)
    backup_file.write(u'<smses count="0">                                           \n')
    backup_file.write(u"<!--Converted from GV Takeout data -->\n")
    backup_file.close()

    ################
    backup_file = open(call_backup_filename, 'w')
    backup_file.write(xml_header)
    backup_file.write(u'<calls count="0">                                           \n')
    backup_file.write(u"<!--Converted from GV Takeout data -->\n")
    backup_file.close()

def write_real_headers():
    print()

    if os.path.exists(sms_backup_filename):
        backup_file = open(sms_backup_filename, 'r+')
        backup_file.write(xml_header)
        backup_file.write(u'<smses count="' + str(num_sms) + u'">\n')
        backup_file.close()
    print(">>", num_sms, "SMS/MMS records written to", sms_backup_filename)

    ################
    if os.path.exists(vm_backup_filename):
        backup_file = open(vm_backup_filename, 'r+')
        backup_file.write(xml_header)
        backup_file.write(u'<smses count="' + str(num_vms) + u'">\n')
        backup_file.close()
    print(">>", num_vms, "Voicemail records written to", vm_backup_filename)

    ################
    if os.path.exists(call_backup_filename):
        backup_file = open(call_backup_filename, 'r+')
        backup_file.write(xml_header)
        backup_file.write(u'<calls count="' + str(num_calls) + u'">\n')
        backup_file.close()
    print(">>", num_calls, "Call records written to", call_backup_filename)

def prep_output_files():
    sms_backup_filename_BAK = sms_backup_filename + '.BAK'
    if os.path.exists(sms_backup_filename):
        if os.path.exists(sms_backup_filename_BAK):
            print('>> Removing', os.path.abspath(sms_backup_filename_BAK))
            os.remove(sms_backup_filename_BAK)
        print('>> Renaming existing SMS/MMS output file to', os.path.abspath(sms_backup_filename_BAK))
        os.rename(sms_backup_filename, sms_backup_filename_BAK)

    print('>> SMS/MMS will be written to',  sms_backup_filename, 'aka', os.path.abspath(sms_backup_filename))
    print(">>")

    call_backup_filename_BAK = call_backup_filename + '.BAK'
    if os.path.exists(call_backup_filename):
        if os.path.exists(call_backup_filename_BAK):
            print('>> Removing', os.path.abspath(call_backup_filename_BAK))
            os.remove(call_backup_filename_BAK)
        print('>> Renaming existing Calls output file to', os.path.abspath(call_backup_filename_BAK))
        os.rename(call_backup_filename, call_backup_filename_BAK)

    print('>> Call history will be written to', call_backup_filename, 'aka', os.path.abspath(call_backup_filename))
    print(">>")

    vm_backup_filename_BAK = vm_backup_filename + '.BAK'
    if os.path.exists(vm_backup_filename):
        if os.path.exists(vm_backup_filename_BAK):
            print('>> Removing', os.path.abspath(vm_backup_filename_BAK))
            os.remove(vm_backup_filename_BAK)
        print('>> Renaming existing Voicemail output file to', os.path.abspath(vm_backup_filename_BAK))
        os.rename(vm_backup_filename, vm_backup_filename_BAK)

    print('>> Voicemail MMS will be written to', vm_backup_filename, 'aka', os.path.abspath(vm_backup_filename))
    print(">>")

    if os.path.exists(contact_number_file):
        with open(contact_number_file) as cnf: 
            cn_data = cnf.read() 
            contacts = json.loads(cn_data)
            print('>> Consulting JSON contacts file', os.path.abspath(contact_number_file))
    else:
            print('>> No (optional) JSON contacts file', os.path.abspath(contact_number_file))

    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

# In some extreme cases, we have to pick our the correspondent from the name
# of the file. It can be a phone number or a contact name, or it can be completely missing.
def get_name_or_number_from_filename():
    global phone_number_from_filename, contact_name_from_filename
    phone_number_from_filename = None
    contact_name_from_filename = None
    # phone number with optional "+"
    match_phone_number = re.match(r'(\+?[0-9]+) - ', html_filename_basename)
    if match_phone_number:
        phone_number_from_filename = match_phone_number.group(1)
    else:
        # sometimes a single " - ", sometimes two of them
        match_name = re.match(r'([^ ].*) - .+ - ', html_filename_basename)
        if not match_name:
            match_name = re.match(r'([^ ].*) - ', html_filename_basename)
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
def scan_vcards_for_contacts(parent_elt):
    global me
    not_me_vcard_number = None
    vcard_elts = parent_elt.find_all(class_="vcard")
    for vcard_elt in vcard_elts:
        this_number, this_name = get_number_and_name_from_tel_elt_parent(vcard_elt)
        if this_number:
            not_me_vcard_number = this_number
            # In case of conflicts, last writer wins
            existing_number = contacts.get(this_name, None)
            contacts[this_name] = this_number
            if this_name == "Me":
                me = this_number
            if this_name and existing_number:
                if this_number != existing_number and not this_name in conflicting_contacts:  # only complain once per conflicting name
                    conflicting_contacts.add(this_name)
                    print()
                    print(f'>> Info: conflicting information about "{this_name}":', existing_number, this_number)
                    print(f'      due to File: "{html_filename_abs_path}"')
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
