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

sms_backup_filename = "../../../sms-gvoice-all.xml"

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

print('New file will be saved to ' + sms_backup_filename)

contacts = json.loads('{}')

# this is for some internal bookkeeping; you don't need to do anything with it.
missing_contacts = json.loads('{}')

if os.path.exists(contact_number_file):
    with open(contact_number_file) as cnf: 
        cn_data = cnf.read() 
        contacts = json.loads(cn_data)
        print('Consulting contacts file ' + contact_number_file)

me = contacts.get(".me", me)
print('Your "me" number is ' + me)

def main():
    print('Checking directory for *.html SMS/MMS files')
    num_sms = 0
    root_dir = '.'

    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            sms_filename = os.path.join(subdir, file)

            try:
                # Original had cp850 (Latin-1), but these are XML files encoded with UTF-8
                sms_file = open(sms_filename, 'r', encoding="utf-8")
            except FileNotFoundError:
                continue

            if(os.path.splitext(sms_filename)[1] != '.html'):
                # print(sms_filename,"- skipped")
                continue
            if re.search(r' - Missed|Placed|Received|Voicemail - ', sms_filename):  # various voice things
                continue

            # printing this just adds clutter, making you miss any interesting output
            # print('Processing ' + sms_filename)

            is_group_conversation = re.match(r'(^Group Conversation)', file)

            soup = BeautifulSoup(sms_file, 'html.parser')

            messages_raw = soup.find_all(class_='message')
            title_whole = soup.find('title').get_text().strip()
            if re.match(r'(^Placed call to)', title_whole):
                # this is a call log, not a message
                continue
            
            correspondent = title_whole
            if re.match(r'(^Me to)', title_whole):  # no, no, not "#Metoo" :-)
                correspondent = title_whole[5:].strip()

            num_sms += len(messages_raw)

            if is_group_conversation:
                participants_raw = soup.find_all(class_='participants')
                write_mms_messages(participants_raw, subdir, messages_raw, sms_filename, correspondent)
            else:
                write_sms_messages(file, subdir, messages_raw, sms_filename, correspondent)


    sms_backup_file = open(sms_backup_filename, 'a')
    sms_backup_file.write(u'</smses>')
    sms_backup_file.close()

    write_header(sms_backup_filename, num_sms)


def contact_name_to_number(contact_name):
    contact_number = contacts.get(contact_name, "0")
    if contact_number == "0" and missing_contacts.get(contact_name, "X") == "X":
        print(contact_number_file + ': add a phone number for contact "' + contact_name + '": "",')
        # we add this fake entry to a dictionary so we don't keep complaining about the same thing
        missing_contacts[contact_name] = "0"
    return contact_number

def write_sms_messages(file, subdir, messages_raw, sms_filename, correspondent):
    fallback_number = 0
    title_has_number = re.search(r"(^\+*[0-9]+)", file)
    if title_has_number:
        fallback_number = title_has_number.group()

    sms_values = {'participants' : get_first_phone_number(messages_raw, fallback_number, correspondent)}

    sms_backup_file = open(sms_backup_filename, 'a')
    for i in range(len(messages_raw)):
        sms_values['type'] = get_message_type(messages_raw[i])
        sms_values['message'] = get_message_text(messages_raw[i])
        sms_values['time'] = get_time_unix(messages_raw[i])
        sms_text = ('<sms protocol="0" address="%(participants)s" '
                    'date="%(time)s" type="%(type)s" '
                    'subject="null" body="%(message)s" '
                    'toa="null" sc_toa="null" service_center="null" '
                    'read="1" status="1" locked="0" /> \n' % sms_values)
        sms_backup_file.write("<!-- file: '" + sms_filename + "' -->\n")
        sms_backup_file.write(sms_text)
        write_img_attachment(messages_raw[i],subdir,sms_backup_file,sms_values)

    sms_backup_file.close()

def write_img_attachment(message,subdir,sms_backup_file,mms_values,participants=None):

    #img = re.search(r"<img src=\"(.*?)\"",message)
    img_tag = message.find('img')
    if img_tag:
        if participants is None:
            participants = [mms_values['participants'],me]

        sent_by_me = mms_values['type'] == 2
        sender = me if sent_by_me else mms_values['participants']

        mms_values['participants_xml'] = get_participants_xml(participants,sender,sent_by_me)
        mms_values['m_type'] = 128 if sent_by_me else 132
        mms_values['img_file'] = img_tag['src'][:50] + '.jpg'
        mms_values['time'] += 1

        img_file_full_path = os.path.join(subdir, mms_values['img_file'])
        if (os.path.exists(img_file_full_path)):
            img_file = open(img_file_full_path, 'rb') 

            mms_values['img_data'] = base64.b64encode(img_file.read()).decode()

            mms_text = ('<mms address="%(participants)s" ct_t="application/vnd.wap.multipart.related" '
                    'date="%(time)s" m_type="%(m_type)s" msg_box="%(type)s" read="1" '
                    'rr="129" seen="1" sub_id="-1" text_only="1"> \n'
                    '  <parts> \n'
                    '    <part seq="0" ct="image/jpeg" name="%(img_file)s" chset="null" cd="null" fn="null" cid="&lt;0&gt;" cl="%(img_file)s" ctt_s="null" ctt_t="null" text="null" sef_type="0" data="%(img_data)s"/> \n'
                    '  </parts> \n'
                    '  <addrs> \n'
                    '%(participants_xml)s'
                    '  </addrs> \n'
                    '</mms> \n' % mms_values)

            img_file.close()
            sms_backup_file.write(mms_text)
            return True
        else:
            return False
    else:
        return False


def write_mms_messages(participants_raw, subdir, messages_raw, sms_filename, correspondent):
    sms_backup_file = open(sms_backup_filename, 'a')

    participants = get_participant_phone_numbers(participants_raw, correspondent)
    mms_values = {'participants' : '~'.join(participants)}

    participants.append(me)

    for i in range(len(messages_raw)):
        sender = get_mms_sender(messages_raw[i], correspondent)
        sent_by_me = sender not in participants

        mms_values['type'] = get_message_type(messages_raw[i])
        mms_values['message'] = get_message_text(messages_raw[i])
        mms_values['time'] = get_time_unix(messages_raw[i])
        mms_values['participants_xml'] = get_participants_xml(participants,sender,sent_by_me)
        mms_values['msg_box'] = 2 if sent_by_me else 1
        mms_values['m_type'] = 128 if sent_by_me else 132

        mms_text = ('<mms address="%(participants)s" ct_t="application/vnd.wap.multipart.related" '
                    'date="%(time)s" m_type="%(m_type)s" msg_box="%(msg_box)s" read="1" '
                    'rr="129" seen="1" sub_id="-1" text_only="1"> \n'
                    '  <parts> \n'
                    '    <part ct="text/plain" seq="0" text="%(message)s"/> \n'
                    '  </parts> \n'
                    '  <addrs> \n'
                    '%(participants_xml)s'
                    '  </addrs> \n'
                    '</mms> \n' % mms_values)

        sms_backup_file.write("<!-- file: '" + sms_filename + "' -->\n")
        sms_backup_file.write(mms_text)
        write_img_attachment(messages_raw[i],subdir,sms_backup_file,mms_values,participants)
        
    sms_backup_file.close()

def get_participants_xml(participants,sender,sent_by_me):
    participants_xml = u''
    for participant in participants:
        participant_is_sender = participant == sender or (sent_by_me and participant == me)
        participant_values = {'number': participant, 'code': 137 if participant_is_sender else 151}
        participants_xml += ('    <addr address="%(number)s" charset="106" type="%(code)s"/> \n' % participant_values)
    return participants_xml

def get_message_type(message): # author_raw = messages_raw[i].cite
    author_raw = message.cite
    if ( not author_raw.span ):
        return 2
    else:
        return 1

    return 0

def get_message_text(message):
    return BeautifulSoup(message.find('q').text,'html.parser').prettify(formatter='html').strip().replace('"',"'")

def get_mms_sender(message, correspondent):
    number = format_number(phonenumbers.parse(message.cite.a['href'][4:], None))
    if number is None:
        number = contact_name_to_number(correspondent)
    else:
        fn_raw = message.cite.span
        if fn_raw is not None:
            fn = fn_raw.get_text().strip()
            if fn != ""  and contacts.get(fn, None) is None:
                contacts[fn] = number # for future reference

    return number
    
def get_first_phone_number(messages, fallback_number, correspondent):
    # handle group messages
    for author_raw in messages:
        if (not author_raw.span):
           continue

        sender_data = author_raw.cite

        try:
            raw_number = sender_data.a['href'][4:]
            if raw_number == "" or raw_number is None:
                raw_number = contact_name_to_number(correspondent)
            else:
                fn = sender_data.span.get_text().strip()
                if fn != ""  and contacts.get(fn, None) is None:
                    contacts[fn] = raw_number # for future reference
                
            phone_number = phonenumbers.parse(raw_number, None)
        except phonenumbers.phonenumberutil.NumberParseException:
            return sender_data.a['href'][4:]

        return format_number(phone_number)

    # fallback case, use number from filename
    if (fallback_number == 0 or len(fallback_number) < 7):
        fallback_number = contact_name_to_number(correspondent)
        return fallback_number
    else:
        return format_number(phonenumbers.parse(fallback_number, None))

def get_participant_phone_numbers(participants_raw, correspondent):
    #participants = [me] # May require adding a contact for "Me" to your phone, with your current number

    participants = []

    for participant_set in participants_raw:
        for participant in participant_set:
            if (not hasattr(participant, 'a')):
                continue

            try:
                raw_number = participant.a['href'][4:]
                if raw_number == "" or raw_number is None:
                    raw_number = contact_name_to_number(correspondent)
                phone_number = phonenumbers.parse(raw_number, None)
            except phonenumbers.phonenumberutil.NumberParseException:
                participants.push(participant.a['href'][4:])

            participants.append(format_number(phone_number))

    if participants == []:
        participants.push(contact_name_to_number(correspondent))
                
    return participants

def format_number(phone_number):
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

def get_time_unix(message):
    time_raw = message.find(class_='dt')
    ymdhms = time_raw['title']
    time_obj = dateutil.parser.isoparse(ymdhms);
    mstime = timegm(time_obj.timetuple()) * 1000 + time_obj.microsecond / 1000
    return int(mstime)

def write_header(filename, numsms):
    backup_file = open(filename, 'r')
    backup_text = backup_file.read()
    backup_file.close()

    backup_file = open(filename, 'w')
    backup_file.write(u"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n")
    backup_file.write(u"<!--Converted from GV Takeout data -->\n")
    backup_file.write(u'<smses count="' + str(numsms) + u'">\n')
    backup_file.write(backup_text)
    backup_file.close()

main()
