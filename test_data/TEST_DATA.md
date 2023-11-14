# Test data

The files under here are for limited regression testing.
I hope they cover all interesting cases,
but it's difficult to say for sure.
The directory structure represents an unpacked Google Takeout archive,
so the interesting stuff is under `Takeout/Voice/Calls/`.
If you run the script from that directory and the default options,
the output files will end up here (the same directory as this file).

The data came mostly from actual Google Takeout files,
but the contact names and numbers have been faked for privacy.
Likewise, the attachment files have been munged, 
which also makes them a lot smaller and easier to inspect in the output files.
All images and sound files have had the same replacement,
so don't let that bother you.
The important thing for the test data is that the attachments show up where expected;
their contents is unimportant.

## Archive browser
The file <archive_browser.html> is a stripped down copy of an actual file from Google Takeout
with line items added for the test data.
It's just here for convenience of browsing the test data files.

## Contacts
Here are the possible contact names and numbers.
You don't need to add any of these to `contacts.json`
unless instructed to do so by the script.
Some of the contacts have multiple phone numbers,
which happens for legitimate reasons in real data.

For this test data, the Google Voice account belongs to user Maria S Curie.

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
with only real calls and conversations and none of the fake ones.

## Console output
Your paths will be different, but my output looks like this:
```
>> Removing /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-gvoice-all.xml.BAK
>> Renaming existing SMS/MMS output file to /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-gvoice-all.xml.BAK
>> SMS/MMS will be written to ../../../sms-gvoice-all.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-gvoice-all.xml
>>
>> Removing /home/wjc/git/gvoice-sms-takeout-xml/test_data/calls-gvoice-all.xml.BAK
>> Renaming existing Calls output file to /home/wjc/git/gvoice-sms-takeout-xml/test_data/calls-gvoice-all.xml.BAK
>> Call history will be written to ../../../calls-gvoice-all.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/calls-gvoice-all.xml
>>
>> Removing /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-vm-gvoice-all.xml.BAK
>> Renaming existing Voicemail output file to /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-vm-gvoice-all.xml.BAK
>> Voicemail MMS will be written to ../../../sms-vm-gvoice-all.xml, aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/sms-vm-gvoice-all.xml
>>
>> No (optional) JSON contacts file /home/wjc/git/gvoice-sms-takeout-xml/test_data/contacts.json
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
>> Reading *.html files under ., aka /home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls
>> Deferring: /home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Agatha M Christie - Text - 2023-10-22T17_28_34Z.html
>> Info: conflicting information about "Edson Arantes do Nascimento": +15703214444 {'+17323214444'}
>>    due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Edson Arantes do Nascimento - Voicemail - 2016-05-01T00_16_43Z.html"

TODO: Missing contact phone number in HTML file. Using '0'.
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/ - Placed - 2013-07-29T20_56_11Z.html"
>> Info: conflicting information about "Edson Arantes do Nascimento": +12123214444 {'+15703214444', '+17323214444'}
>>    due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Edson Arantes do Nascimento - Voicemail - 2014-05-17T02_54_27Z.html"
>> Your 'Me' phone number is +17323210011
>> 2nd  pass: /home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Agatha M Christie - Text - 2023-10-22T17_28_34Z.html

TODO: /home/wjc/git/gvoice-sms-takeout-xml/test_data/contacts.json: add a +phonenumber for contact: "Agatha M Christie": "+",
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Agatha M Christie - Text - 2023-10-22T17_28_34Z.html"

>>     62 SMS/MMS records written to ../../../sms-gvoice-all.xml
>>      3 Voicemail records written to ../../../sms-vm-gvoice-all.xml
>>     10 Call records written to ../../../calls-gvoice-all.xml
>>      0 Contact name-and-numbers read from JSON file ../../../contacts.json
>>     12 Contact name-and-numbers discovered in HTML files
>>      1 Files deferred on first pass
>>      2 Conflict warnings given
>>      2 TODO errors given
```
