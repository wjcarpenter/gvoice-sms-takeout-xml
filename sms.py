from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings
warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)
import re
import os
import phonenumbers
import dateutil.parser
import time, datetime
from calendar import timegm
import warnings
import base64
from io import open # adds emoji support
import json
import isodate

# We need *your* phone number (complete with "+" and country code). If you don't
# want to edit this script in this "me" assignment, you can instead create a
# pseudo entry in the "contacts" stuff below. (And if you do that and use the
# separate file, you won't have to edit this script.) The entry must have the contact name
# ".me" (that is, a period followed by the lower case letters "m" and "e"). If that
# is found, it will replace the value from the assignment on the next line.
me = '+1111111111' # enter phone number

# SMS Backup and Restore likes to notice filename that start with "sms-"
# Save it to the great-grandparent directory because it can otherwise be hard to find amongst
# the zillion HTML files. The great-grandparent directory is the one that contains
# "Takeout" as a subdirectory, and you should run this script from the
# Takeout/Voice/Calls subdirectory.

sms_backup_filename      = "../../../sms-gvoice-all.xml"
sms_backup_filename_BAK  = "../../../sms-gvoice-all.xml.BAK"
call_backup_filename     = "../../../calls-gvoice-all.xml"
call_backup_filename_BAK = "../../../calls-gvoice-all.xml.BAK"
vm_backup_filename       = "../../../sms-vm-gvoice-all.xml"
vm_backup_filename_BAK   = "../../../sms-vm-gvoice-all.xml.BAK"

# We sometimes see isolated messages from ourselves to someone, and the Takeout format
# only identifies them by contact name instead of phone number. In such cases, we
# consult this optional JSON file to map  the name to a phone number (which should
# include the "+" and country code and no other punctuation). Must be valid JSON, eg:
# {
#   ".me": "+441234567890",
#   "Joe Blow": "+18885551234",
#   "Susie Glow": "+18885554321"
# }
# In cases where there is no JSON entry when needed, a warning is printed. Update
# the JSON file and re-run this script. Don't try to restore with the output
# file until you have resolved all of those contacts warnings.

# This file is *optional*, and you can just put your data directly into the "contacts = json.loads('{}')
# line below if you feel like it.
contact_number_file = "../../../contacts.json"
contacts = json.loads('{}')

# this is for some internal bookkeeping; you don't need to do anything with it.
missing_contacts = json.loads('{}')
me = ""

# some global counters
num_sms = 0
num_calls = 0
num_vms = 0

# I really don't like globals, but there are just too many things to tote around in all these function calls.
subdir = None
filename_basename = None
filename_rel_path = None
filename_abs_path = None
filename_phone_number = None
filename_contact_name = None
title_phone_number = None
title_contact_name = None
first_vcard_number = None
html_elt = None

def main():
    global filename_basename, filename_rel_path, filename_abs_path, subdir
    global html_elt
    prep_output_files()
    print('Checking', os.getcwd(),'for *.html files')
    come_back_later = []
    write_dummy_headers()

    for subdir, dirs, files in os.walk("."):
        for filename_basename in files:
            process_one_file(True, come_back_later)

    if not me and come_back_later:
        print("Unfortunately, we can't figure out your own phone number.")
    else:
        for subdir, filename_basename in come_back_later:
            process_one_file(False, come_back_later)

    sms_backup_file = open(sms_backup_filename, 'a'); sms_backup_file.write(u'</smses>\n'); sms_backup_file.close()
    vm_backup_file = open(vm_backup_filename, 'a'); vm_backup_file.write(u'</smses>\n'); vm_backup_file.close()
    call_backup_file = open(call_backup_filename, 'a'); call_backup_file.write(u'</calls>\n'); call_backup_file.close()
    write_real_headers()

def process_one_file(first_pass, come_back_later):
    global filename_rel_path, filename_abs_path
    global html_elt
    filename_rel_path = os.path.join(subdir, filename_basename)

    html_file = open(filename_rel_path, 'r', encoding="utf-8")
    if not filename_basename.endswith('.html'): return
    name_or_number_from_filename()
    filename_abs_path = os.path.abspath(filename_rel_path)
    html_elt = BeautifulSoup(html_file, 'html.parser')
    name_or_number_from_title()

    tags_div = html_elt.body.find(class_='tags')
    tag_elts = tags_div.find_all(rel='tag')
    tag_value_list = []
    for tag_elt in tag_elts:
        tag_value = tag_elt.get_text()
        tag_value_list.append(tag_value)

    first_vcard_number = None
    find_contacts_in_vcards(html_elt.body)
    need_title_contact = title_contact_name and not contacts.get(title_contact_name, None)
    need_filename_contact = filename_contact_name and not contacts.get(filename_contact_name, None)
    if first_pass and (not me or need_title_contact or need_filename_contact):
        if "Text" in tag_value_list or "Voicemail" in tag_value_list or "Recorded" in tag_value_list:
            # Can't do anything rational for SMS/MMS if we don't know our own number.
            # We _might_ be able to get along without the phone numbers for the contacts
            # named in the filename or the HTML title, but not always. Save them for
            # the second pass just in case.
            print("Deferring (don't worry about it):", filename_abs_path)
            come_back_later.append([subdir, filename_basename])
            return

    if   "Text"      in tag_value_list:  process_Text()
    elif "Received"  in tag_value_list:  process_call(1)
    elif "Placed"    in tag_value_list:  process_call(2)
    elif "Missed"    in tag_value_list:  process_call(3)
    elif "Voicemail" in tag_value_list:  process_Voicemail()
    elif "Recorded"  in tag_value_list:  process_Voicemail()
    else:
        print("Unrecognized tag situation '" + str(tag_value_list) + "'; silently ignoring file '" + filename_rel_path + "'")

# In some extreme cases, we have to pick our the correspondent from the name
# of the file. It can be a phone number or a contact name, or it can be completely missing.
def name_or_number_from_filename():
    global filename_phone_number, filename_contact_name
    filename_phone_number = None
    filename_contact_name = None
    # phone number with optional "+"
    match = re.match(r'(\+?[0-9]+) - ', filename_basename)
    if match:
        filename_phone_number = match.group(1)
    else:
        # sometimes a single " - ", sometimes two of them
        match = re.match(r'([^ ].*) - .+ - ', filename_basename)
        if not match:
            match = re.match(r'([^ ].*) - ', filename_basename)
        if match:
            filename_contact_name = match.group(1)
            if filename_contact_name == "Group Conversation":
                filename_contact_name = None

def name_or_number_from_title():
    global title_phone_number, title_contact_name
    title_phone_number = None
    title_contact_name = None
    title_elt = html_elt.find('head').find('title')
    title_value = title_elt.get_text()
    split = title_value.split("\n")
    correspondent = split[len(split)-1].strip()
    
    if not correspondent:
        return

    match = re.match(r'(\+?[0-9]+)', correspondent)
    if match:
        # I think this doesn't actually happen
        title_phone_number = match.group(1)
    else:
        title_contact_name = correspondent
        if title_contact_name == "Group Conversation":
            title_contact_name = None

def find_contacts_in_vcards(parent_elt):
    global me, first_vcard_number
    vcard_elts = parent_elt.find_all(class_="vcard")
    for i in range(len(vcard_elts)):
        vcard_elt = vcard_elts[i]
        tel_elt = vcard_elt.find(class_='tel')
        if tel_elt: # vcard attachments also get the "vcard" CSS class
            href_attr = tel_elt['href']
            if href_attr:
                if href_attr.startswith("tel:"):
                    href_attr = href_attr[4:]
                    if not href_attr:
                        continue
                this_number = href_attr
                if i == 0:
                    first_vcard_number = this_number
                fn_elt = vcard_elt.find(class_="fn")
                if fn_elt:
                    this_name = fn_elt.get_text()
                    # Sometimes the "name" ends up being a repeat of the phone number
                    if this_name and not re.match(r'\+?[0-9]+', this_name):
                        if this_name == "Me":
                            me = this_number
                        else:
                            contacts[this_name] = this_number

# Information needs:
#
# Calls: 
#
#   number="%(telephone_number)s"     # phone number of the call
#   duration="%(duration)s"           # duration of the call in seconds
#   date="%(timestamp)s"              # Java date representation of the time when the call was sent/received
#   type="%(type)s"                   # 1 = Incoming, 2 = Outgoing, 3 = Missed, 4 = Voicemail, 5 = Rejected, 6 = Refused List.
#   presentation="%(presentation)s"   # caller id presentation info. 1 = Allowed, 2 = Restricted, 3 = Unknown, 
#
# simple SMS:
#
#   address="%(participants)s"         # phone number of the sender/recipient
#   date="%(timestamp)s"               # Java date representation of the time when the message was sent/received.
#   type="%(type)s"                    # 1 = Received, 2 = Sent
#   body="%(message)s"                 # content of the message
#
# MMS for groups or with attachments
#
#   address="%(participants)s"         # phone number of the sender/recipient
#   date="%(timestamp)s"               # Java date representation of the time when the message was sent/received
#   m_type="%(m_type)s"                # The type of the message defined by MMS spec.
#   msg_box="%(type)s"                 # 1 = Received, 2 = Sent
#   text="%(the_text)s"                # content of the message (is this ever anything?)
#   '%(participants_xml)s'             # address - phone number of the sender/recipient; type - 151 = To, 137 = From
#
# for IMG/AUDIO attachment
#    ct="%(content_type)s"             # content type
#    name="%(attachment_file)s"        # name of the part
#    cl="%(attachment_file)s"          # content location
#    data="%(img_data)s"               # base64 encoded binary content
#

# Naming conventions for things read from an HTML file:
#   foo_elts   a collection of XML elements 
#   foo_elt    a single XML element
#   bar_attr   the value of an XML element "bar" attribute
#   foo_value  the value (text content) of an XML element



def process_Text():
    # This can be either SMS or MMS. MMS can be either with or without attachments.
    message_elts = html_elt.find_all(class_='message')
    participant_elt = html_elt.find(class_='participants')

    if participant_elt:
        write_mms_messages(participant_elt, message_elts)
    else:
        write_sms_messages(message_elts)

def process_Voicemail():
    process_call(4)
    body = html_elt.find('body')
    write_sms_message_for_vm(body)

def process_call(type):
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
    timestamp = to_timestamp(iso_date)
    duration_elt = html_elt.find(class_="duration")
    if not duration_elt:
        duration = 0
    else:
        iso_duration = duration_elt.attrs['title']
        duration = isodate.parse_duration(iso_duration)
        duration = round(datetime.timedelta.total_seconds(duration))
    write_call_message(telephone_number, presentation, duration, timestamp, type, readable_date)

def write_call_message(telephone_number, presentation, duration, timestamp, type, readable_date):
    global num_sms, num_vms, num_calls
    call_data = {'telephone_number': telephone_number, 'duration': duration, 'timestamp': timestamp, 'type': type, 'readable_date': readable_date, 'presentation': presentation}
    
    call_backup_file = open(call_backup_filename, 'a')
    call_text = ('<call number="%(telephone_number)s" '
                 'duration="%(duration)s" '
                 'date="%(timestamp)s" '
                 'type="%(type)s" '
                 'presentation="%(presentation)s" '
                 'readable_date="%(readable_date)s" '
                 ' />\n' % call_data)
    call_backup_file.write("<!-- file: '" + filename_rel_path + "' -->\n")
    call_backup_file.write(call_text)

    call_backup_file.close()
    num_calls += 1

def contact_name_to_number(contact_name):
    if not contact_name:
        print("File:", filename_abs_path)
        print("We can't figure out the name or number for a contact in the above file.")
        return "0"
    contact_number = contacts.get(contact_name, None)
    if not contact_number and not missing_contacts.get(contact_name, None):
        print("File:", filename_abs_path)
        print(contact_number_file + ': TODO: add a +phonenumber for contact: "' + contact_name + '": "+",')
        # we add this fake entry to a dictionary so we don't keep complaining about the same thing
        missing_contacts[contact_name] = "0"
    return contact_number

def contact_number_to_name(contact_number):
    if contact_number:
        for name, number in contacts.items():
            if number == contact_number:
                return name
    return None

def get_sender():
    if first_vcard_number:
        sender = first_vcard_number
    elif title_phone_number:
        sender = title_phone_number
    elif title_contact_name:
        sender = contact_name_to_number(title_contact_name)
    elif filename_phone_number:
        sender = filename_phone_number
    elif filename_contact_name:
        sender = contact_name_to_number(filename_contact_name)
    else:
        sender = None
    return sender

def write_sms_messages(message_elts):
    global num_sms, num_vms, num_calls

    for i in range(len(message_elts)):
        message_elt = message_elts[i]
        find_contacts_in_vcards(message_elt)
        sender = first_vcard_number
        sent_by_me = (sender == me)
        the_text = get_message_text(message_elt)
        v_values = {}
        v_values['participants'] = sender
        v_values['type'] = get_message_type(message_elt)
        v_values['message'] = the_text
        v_values['timestamp'] = get_time_unix(message_elt)
        attachments = get_attachments(message_elt)
        # if it was just an image with no text, there is no point in creating an empty SMS to go with it
        if the_text and the_text != "MMS Sent" and not attachments:
            sms_text = ('<sms protocol="0" address="%(participants)s" '
                        'date="%(timestamp)s" type="%(type)s" '
                        'subject="null" body="%(message)s" '
                        'toa="null" sc_toa="null" service_center="null" '
                        'read="1" status="1" locked="0" /> \n' % v_values)
            sms_backup_file = open(sms_backup_filename, 'a')
            sms_backup_file.write("<!-- file: '" + filename_rel_path + "' -->\n")
            sms_backup_file.write(sms_text)
            sms_backup_file.close()
            num_sms += 1
        else:
            v_values['the_text'] = the_text
            v_values['sender'] = sender
            v_values['sent_by_me'] = sent_by_me
            v_values['filename_rel_path'] = filename_rel_path
            write_attachments(message_elt, v_values, attachments)

def write_sms_message_for_vm(body):
    global num_sms, num_vms, num_calls
    sender = get_sender()
    v_values = {}
    v_values['participants'] = sender
    v_values['timestamp'] = get_time_unix(body)
    sender_name = contact_number_to_name(sender)
    v_values['the_text'] = "Voicemail/Recording from " + (sender_name if sender_name else sender)
    v_values['sender'] = sender
    v_values['sent_by_me'] = False
    v_values['filename_rel_path'] = filename_rel_path
    v_values['type'] = "1"
    write_attachments(body, v_values, get_attachments(body), [sender])

def get_attachments(message_elt):
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

def write_attachments(message_elt, v_values, attachment_elts, participants=None):
    global num_sms, num_vms, num_calls
    if not participants:
        participants = [v_values['participants'],me]
    v_values['participants'] = '~'.join(participants)

    v_values['participants_xml'] = get_participants_xml(participants, v_values['sender'], v_values['sent_by_me'])
    v_values['m_type'] = 128 if v_values['sent_by_me'] else 132
    mms_head = ('<mms address="%(participants)s" ct_t="application/vnd.wap.multipart.related" '
                'date="%(timestamp)s" m_type="%(m_type)s" msg_box="%(type)s" read="1" '
                'rr="129" seen="1" sub_id="-1" text_only="0"> \n'
                '  <addrs> \n'
                '%(participants_xml)s'
                '  </addrs> \n'
                '  <parts> \n'
                % v_values)

    mms_text = ("    <!-- file: '" + filename_rel_path + "' -->\n"
                '    <part seq="-1" ct="text/plain" name="null" chset="106" cd="null" fn="null" '
                'cid="&lt;text000001&gt;" cl="text000001" ctt_s="null" ctt_t="null" text="%(the_text)s"/> \n'
                % v_values)

    mms_tail = ('  </parts> \n'
                '</mms> \n'
                % v_values)

    sms_init = False
    vms_init = False
    sms_backup_file = open(sms_backup_filename, 'a')
    vms_backup_file = open(vm_backup_filename, 'a')

    if attachment_elts:
        for i in range(len(attachment_elts)):
            attachment_elt = attachment_elts[i]
            sequence_number = i
            if attachment_elt.name == 'img':
                if not sms_init:
                    sms_backup_file.write(mms_head)
                    sms_backup_file.write(mms_text)
                    sms_init = True
                attachment_file_ref = attachment_elt['src']
                write_attachment_common("image", sms_backup_file, sequence_number, attachment_file_ref)
                num_sms += 1
            elif attachment_elt.name == 'audio':
                if not vms_init:
                    vms_backup_file.write(mms_head)
                    vms_backup_file.write(mms_text)
                    vms_init = True
                attachment_file_ref = attachment_elt.a['href']
                write_attachment_common("audio", vms_backup_file, sequence_number, attachment_file_ref)
                num_vms += 1
            elif attachment_elt.name == 'a' and 'vcard' in attachment_elt['class']:
                if not sms_init:
                    sms_backup_file.write(mms_head)
                    sms_backup_file.write(mms_text)
                    sms_init = True
                attachment_file_ref = attachment_elt['href']
                write_attachment_common("vcard", sms_backup_file, sequence_number, attachment_file_ref)
                num_vms += 1
            else:
                print("Unrecognized MMS attachment in file", filename_abs_path, ":\n", attachment)

    if sms_init:
        sms_backup_file.write(mms_tail)
    if vms_init:
        vms_backup_file.write(mms_tail)
    sms_backup_file.close()
    vms_backup_file.close()

def write_attachment_common(attachment_type, backup_file, sequence_number, attachment_file_ref):
    attachment_filename, content_type = figure_out_attachment_file_and_type(attachment_type, attachment_file_ref)
    if not attachment_filename:
        return
    attachment_filename_rel_path = os.path.join(subdir, attachment_filename)
    attachment_file = open(attachment_filename, 'rb') 
    attachment_data = base64.b64encode(attachment_file.read()).decode()
    attachment_file.close()
    backup_text = (
        "    <!-- file: '" + attachment_filename_rel_path + "-->\n"
        '    <part seq="' + str(sequence_number) + '"' 
        ' ct="' + content_type + '"'
        ' name="' + attachment_filename + '"'
        ' chset="null" cd="null" fn="null" cid="&lt;0&gt;" ctt_s="null" ctt_t="null" text="null" sef_type="0" '
        ' cl="' + attachment_filename + '"'
        ' data="' + attachment_data + '"'
        ' /> \n')
    backup_file.write(backup_text)

def figure_out_attachment_file_and_type(attachment_type, attachment_file_ref):
    base, ext = os.path.splitext(attachment_file_ref)
    attachment_filename, content_type = consider_this_attachment_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    base = base[:50]  # this is odd; probably bugs in Takeout or at least weird choices
    attachment_filename, content_type = consider_this_attachment_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    base, ext = os.path.splitext(filename_basename)
    attachment_filename, content_type = consider_this_attachment_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type
        
    base = base[:50]  # this is odd; probably bugs in Takeout or at least weird choices
    attachment_filename, content_type = consider_this_attachment_candidate(base, attachment_type)
    if attachment_filename:
        return attachment_filename, content_type

    print(attachment_type, "attachment referenced in message, but not found:", os.path.abspath(os.path.join(subdir, attachment_file_ref)))
    print("  src='" + attachment_file_ref + "'")
    print("  referenced from", filename_abs_path)
    return None, None
    
def consider_this_attachment_candidate(base, attachment_type):
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
    
def write_mms_messages(participant_elt, message_elts):
    global num_sms, num_vms, num_calls
    sms_backup_file = open(sms_backup_filename, 'a')

    participants = get_participant_phone_numbers(participant_elt)
    v_values = {'participants' : '~'.join(participants)}

    for i in range(len(message_elts)):
        message_elt = message_elts[i]
        find_contacts_in_vcards(message_elt)
        sender = first_vcard_number
        sent_by_me = sender not in participants
        the_text = get_message_text(message_elt)
        v_values['type'] = get_message_type(message_elt)
        v_values['message'] = the_text
        v_values['timestamp'] = get_time_unix(message_elt)
        v_values['participants_xml'] = get_participants_xml(participants, sender, sent_by_me)
        v_values['msg_box'] = 2 if sent_by_me else 1
        v_values['m_type'] = 128 if sent_by_me else 132
        attachments = get_attachments(message_elt)

        if the_text and the_text != "MMS Sent" and not attachments:
            mms_text = ('<mms address="%(participants)s" ct_t="application/vnd.wap.multipart.related" '
                        'date="%(timestamp)s" m_type="%(m_type)s" msg_box="%(msg_box)s" read="1" '
                        'rr="129" seen="1" sub_id="-1" text_only="1"> \n'
                        '  <addrs> \n'
                        '%(participants_xml)s'
                        '  </addrs> \n'
                        '  <parts> \n'
                        '    <part ct="text/plain" seq="0" text="%(message)s"/> \n'
                        '  </parts> \n'
                        '</mms> \n' % v_values)

            sms_backup_file.write("<!-- file: '" + filename_rel_path + "' -->\n")
            sms_backup_file.write(mms_text)
            num_sms += 1
        else:
            v_values['the_text'] = the_text
            v_values['sender'] = sender
            v_values['sent_by_me'] = sent_by_me
            v_values['filename_rel_path'] = filename_rel_path
            write_attachments(message_elt, v_values, attachments, participants)
    sms_backup_file.close()

def get_participants_xml(participants,sender,sent_by_me):
    participants_xml = u''
    temp_list = participants.copy()
    temp_list.append(me)
    for participant in temp_list:
        participant_is_sender = participant == sender or (sent_by_me and participant == me)
        participant_values = {'number': participant, 'code': 137 if participant_is_sender else 151}
        participants_xml += ('    <addr address="%(number)s" charset="106" type="%(code)s"/> \n' % participant_values)
    return participants_xml

def get_message_type(message): # author_elt = message_elts[i].cite
    author_elt = message.cite
    if ( not author_elt.span ):
        return 2
    else:
        return 1

    return 0

def get_message_text(message_elt):
    text_elt = message_elt.find('q')
    if not text_elt:
        return ""
    return BeautifulSoup(text_elt.text,'html.parser').prettify(formatter='html').strip().replace('"',"'")

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
                    raw_number = contact_name_to_number(get_sender())
                phone_number = phonenumbers.parse(raw_number, None)
            except phonenumbers.phonenumberutil.NumberParseException:
                participants.append(participant.a['href'][4:])

            participants.append(format_number(phone_number))

    if participants == []:
        participants.append(contact_name_to_number(title_correspondent))
                
    return participants

def format_number(phone_number):
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

def to_timestamp(iso_time):
    time_obj = dateutil.parser.isoparse(iso_time);
    mstime = timegm(time_obj.timetuple()) * 1000 + time_obj.microsecond / 1000
    return int(mstime)

def get_time_unix(message):
    time_elt = message.find(class_='dt')
    if not time_elt:
        time_elt = message.find(class_='published')
    ymdhms = time_elt['title']
    return to_timestamp(ymdhms)

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
    global num_sms, num_vms, num_calls
    print()

    if os.path.exists(sms_backup_filename):
        backup_file = open(sms_backup_filename, 'r+')
        backup_file.write(u"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n")
        backup_file.write(u'<smses count="' + str(num_sms) + u'">\n')
        backup_file.close()
    print(num_sms, "SMS/MMS records written to", sms_backup_filename)

    ################
    if os.path.exists(vm_backup_filename):
        backup_file = open(vm_backup_filename, 'r+')
        backup_file.write(u"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n")
        backup_file.write(u'<smses count="' + str(num_vms) + u'">\n')
        backup_file.close()
    print(num_vms, "Voicemail records written to", vm_backup_filename)

    ################
    if os.path.exists(call_backup_filename):
        backup_file = open(call_backup_filename, 'r+')
        backup_file.write(u"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n")
        backup_file.write(u'<calls count="' + str(num_calls) + u'">\n')
        backup_file.close()
    print(num_calls, "Call records written to", call_backup_filename)

def prep_output_files():
    if os.path.exists(sms_backup_filename):
        if os.path.exists(sms_backup_filename_BAK):
            print('>> Removing', os.path.abspath(sms_backup_filename_BAK))
            os.remove(sms_backup_filename_BAK)
        print('>> Renaming existing SMS/MMS output file to', os.path.abspath(sms_backup_filename_BAK))
        os.rename(sms_backup_filename, sms_backup_filename_BAK)

    print('>> SMS/MMS will be written to',  sms_backup_filename, 'aka', os.path.abspath(sms_backup_filename))
    print(">>")

    if os.path.exists(call_backup_filename):
        if os.path.exists(call_backup_filename_BAK):
            print('>> Removing', os.path.abspath(call_backup_filename_BAK))
            os.remove(call_backup_filename_BAK)
        print('>> Renaming existing Calls output file to', os.path.abspath(call_backup_filename_BAK))
        os.rename(call_backup_filename, call_backup_filename_BAK)

    print('>> Call history will be written to', sms_backup_filename, 'aka', os.path.abspath(sms_backup_filename))
    print(">>")

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


main()
