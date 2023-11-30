# Test data

The files under here are for limited regression testing.
I hope they cover all interesting cases,
but it's difficult to say for sure.
The directory structure represents an unpacked Google Takeout archive,
so the interesting stuff is under `Takeout/Voice/Calls/` and `Takeout/Google Chat/Groups/`.
If you run the script from the `Takeout/` directory and use the default options,
the output files will end up here (the same directory as this file, one level above `Takeout/`).

The data came mostly from actual Google Takeout files,
but the contact names and numbers have been faked for privacy.
Likewise, the attachment files have been munged, 
which also makes them a lot smaller and easier to inspect in the output files.
All images and sound files have had the same replacement,
so don't let that bother you.
The important thing for the test data is that the attachments show up where expected;
their content is unimportant.

## Archive browser
The file <Takeout/archive_browser.html> is a stripped down copy of an actual file from Google Takeout
with line items added for the test data.
It's just here for convenience of browsing the test data files.

## Contacts
Here are the possible contact names and numbers.
You don't need to add any of these to `contacts.json`
(in this directory, one level above `Takeouts/`)
unless instructed to do so by the script.
Some of the contacts have multiple phone numbers,
which happens for legitimate reasons in real data.

For this test data, the Google Voice account belongs to user `Maria S Curie`
(so that phone number is used for `Me`).

| Name | Numbers |
|------|---------|
|Agatha M Christie|+17323211111|
|Alan A Milne|+17323212222|
|Albert Einstein|+17323213333|
|Edson Arantes do Nascimento|+17323214444,+12123214444,+15703214444|
|F Scott Fitzgerald|+17323215555|
|George H Ruth Jr|+17323216666|
|Hans Christian Andersen|+17323217777|
|Maria S Curie|+17323210011|
|Søren Aabye Kierkegaard|+17323211414|
|William Shakespeare|+17323211515|
|Wilma Glodean Rudolph|+17323211717|
|Debbie One|+12125550001|
|Missy Two|+12125550002|
|Trish Three|+12125550003|
|Mary Four|+12125550004|
|Laura Five|+12125550005|

## Testing SMS Backup and Restore
Before committing your own precious message and call history to the `restore` process,
you might like to make a practice run with this test data.
How can you do that?

- In the Google Contacts for the account you use with your phone,
add the names and phone numbers from the above list.
You might like to add some distinctive label to those entries to make them easy find or delete later.
- Run the `sms.py` script against this test data.
- In the output files,
replace Curie's number, `+17323210011`, with your own number.
If you are on a Unix-like system, 
you can do that with `sed` like so:
`sed -i 's/17323210011/19991111234/g' *.xml`
- Use those modified output files to do a `restore` to your phone with SMS Backup and Restore.
- In your phone's dialer app, 
you should be able to see call history for several of those fake contacts.
- In your phone's text messaging app,
you should be able to see conversation history for several of those fake contacts.
That includes a few messages with voicemail recordings attached
and a group conversation with you and 5 other participants.
Some of the messages include attached images or vCard files.
- You might like to `restore` again with the same files to see that SMS Backup and Restore detects the duplicates.
- When you are done looking around,
your dialer and text messaging apps should let you delete the history for all the restored items.
Your contacts app should let you delete the contacts themselves.

After you have done all of the above, your phone's contents should be back where you started,
with only real calls and conversations and none of the fake ones from this test data.

## Console output
Your paths will be different, but my output looks like this (I ran it with the `-z` option to dump the internal tables):
```
>> No (optional) JSON contacts file /home/wjc/git/gvoice-sms-takeout-xml/test_data/contacts.json
>> Removing /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-gvoice.xml.BAK
>> Renaming existing SMS/MMS output file to /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-gvoice.xml.BAK
>> SMS/MMS from Google Voice will be written to ../sms-gvoice.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-gvoice.xml
>>
>> Removing /home/wjc/git/gvoice-sms-takeout-xml/test_data/calls-gvoice.xml.BAK
>> Renaming existing Calls output file to /home/wjc/git/gvoice-sms-takeout-xml/test_data/calls-gvoice.xml.BAK
>> Call history from Google Voice will be written to ../calls-gvoice.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/calls-gvoice.xml
>>
>> Removing /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-vm-gvoice.xml.BAK
>> Renaming existing Voicemail output file to /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-vm-gvoice.xml.BAK
>> Voicemail MMS from Google Voice will be written to ../sms-vm-gvoice.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-vm-gvoice.xml
>>
>> Removing /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-chat.xml.BAK
>> Renaming existing SMS/MMS output file to /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-chat.xml.BAK
>> SMS/MMS from Google Chat will be written to ../sms-chat.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-chat.xml
>>
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
>> 1st pass reading *.html files under Voice/Calls, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls
>> Info: conflicting information about "Edson Arantes do Nascimento": ['+17323214444'] '+15703214444'
>>    due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Edson Arantes do Nascimento - Voicemail - 2016-05-01T00_16_43Z.html"
>> Info: conflicting information about "Edson Arantes do Nascimento": ['+17323214444', '+15703214444'] '+12123214444'
>>    due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Edson Arantes do Nascimento - Voicemail - 2014-05-17T02_54_27Z.html"
>> Your 'Me' phone number is +17323210011
>> 2nd pass reading *.html files under Voice/Calls, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls

TODO: Missing or disallowed +phonenumber for contact: "Agatha M Christie": "+",
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Agatha M Christie - Text - 2023-10-22T17_28_34Z.html"

TODO: Missing contact phone number in HTML file. Using '0000000000'.
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/ - Placed - 2013-07-29T20_56_11Z.html"
>> Reading chat files under Voice/Calls, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls

>> Counters:
>>     62 SMS/MMS records from Google Voice written to ../sms-gvoice.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-gvoice.xml
>>      3 Voicemail records from Google Voice written to ../sms-vm-gvoice.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-vm-gvoice.xml
>>     10 Call records from Google Voice written to ../calls-gvoice.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/calls-gvoice.xml
>>      0 SMS/MMS records from Google Chat written to ../sms-chat.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-chat.xml
>>     14 Contacts discovered in HTML files
>>      2 Conflict info warnings given
>>      2 TODO errors given
>> Recap of conflict info warnings:
>>    Edson Arantes do Nascimento: ['+17323214444', '+15703214444', '+12123214444']
>> Recap of missing or unresolved contacts (not including disallowed numbers):
>>    {'Agatha M Christie'}

Mappings of names-to-numbers (configured and discovered):
{ 'Alan A Milne': [('+17323212222', 1696201093000, False)],
  'Albert Einstein': [('+17323213333', 1558549136000, False)],
  'Debbie One': [('+12125550001', 1696191235000, False)],
  'Edson Arantes do Nascimento': [ ('+17323214444', 1696194960000, False),
                                   ('+15703214444', 1462061803000, False),
                                   ('+12123214444', 1400295267000, False)],
  'Laura Five': [('+12125550005', 1696220436000, False)],
  'Mary Four': [('+12125550004', 1696208230000, False)],
  'Me': [('+17323210011', 1697995714000, False)],
  'Missy Two': [('+12125550002', 1696190939000, False)],
  'Rosalind E Franklin': [('+17323211313', 1626211647000, False)],
  'Søren Aabye Kierkegaard': [('+17323211414', 1696198699000, False)],
  'Trish Three': [('+12125550003', 1696208303000, False)],
  'William Shakespeare': [('+17323211515', 1640039728000, False)]}

Mappings of numbers-to-names (computed reverse mappings)
{ '+12123214444': 'Edson Arantes do Nascimento',
  '+12125550001': 'Debbie One',
  '+12125550002': 'Missy Two',
  '+12125550003': 'Trish Three',
  '+12125550004': 'Mary Four',
  '+12125550005': 'Laura Five',
  '+15703214444': 'Edson Arantes do Nascimento',
  '+17323210011': 'Me',
  '+17323211313': 'Rosalind E Franklin',
  '+17323211414': 'Søren Aabye Kierkegaard',
  '+17323211515': 'William Shakespeare',
  '+17323212222': 'Alan A Milne',
  '+17323213333': 'Albert Einstein',
  '+17323214444': 'Edson Arantes do Nascimento'}

Mappings of names-to-names (configured name aliases):
{}

Mappings of numbers-to-numbers (configured number aliases):
{}
```
