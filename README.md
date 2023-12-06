# gvoice-sms-takeout-xml
Convert Google Voice data and Google Chat data from Google Takeout to XML files suitable for use with SMS Backup and Restore.
Find this code repository at <https://github.com/wjcarpenter/gvoice-sms-takeout-xml>.

Google Takeout, 
<https://takeout.google.com>,
is a tool provided by Google for downloading various kinds of data associated with your Google account.
In this case, it's data from Google Voice or Google Chat or both.
It's exported as a ZIP file containing several individual HTML files and some other file types.
Although the HTML files, like any HTML files, exhibit a certain structure,
the actual format used by Google Takeout is not documented.
(At least, I have not been able to find any documentation.
I'd be glad to be proven wrong, so if you know of some documentation, do please let me know.)
The structure is oriented toward viewing the information in a browser.
Consequently, pulling information out of those HTML files is just reverse engineering.
There are many special cases.
The script deals with all of the special cases that I know about,
but there could easily be more special cases that don't happen to show up in the data that I have to work with.

SMS Backup and Restore, 
<https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore>,
is a popular Android app that can back up your phone's text messages and call history.
The backups are in XML format,
and the app gives you several choices for where to keep them.
The XML format is mostly -- but not completely -- documented.

The script reads the files from Google Takeout and produces files in the XML format for SMS Backup and Restore.
The idea is that you then use those XML files to do a `restore` with the app.
That transfers your Google Voice and Google Chat history into your phone's native history.

## This fork
This is a fork of <https://github.com/karlrees/gvoice-sms-takeout-xml>,
which is itself a fork of <https://github.com/calyptecc/gvoice-sms-takeout-xml>.
Although I have made a massive number of changes, 
so that it does not look much like the originals any more (perhaps it's not even recognizable),
I have kept the same repo name and script name for the sake of being easily found.
I'm grateful to those earlier authors for giving me a starting point,
but there's not much of their code left.

This fork corrects several problems I ran into when using the original scripts.
I also added some significant additional features.

## Apologia
Reverse engineering is a hazardous business.
There are already many special cases and oddities dealt with by the script.
There are undoubtedly more that I either didn't happen to encounter, 
or that I didn't notice.
Google could at any time change the format of the Google Takeout files, 
or (less likely) SMS Backup and Restore could change the requirements for backup files.
I welcome you to bring additional things like that to my attention,
though fixing them up is the usual freebie "best effort" sort of thing.
Undoubtedly, after some months or years, 
I'll myself become a little hazy on the workings of the script,
and that might add some time.

When asking questions or reporting issues,
the best evidence to give is the original data file that provokes the issue.
The script usually names a specific file that gives it a headache.
Sometimes the script will not know that it's misbehaving, 
in which case you have a little detective work to do.
In the XML outputs, input file names are included as XML comments.
For the case of being unable to find referenced attachments,
it's probably some new quirk of the trial and error way the script has of figuring it out.
(There are some bugs/mistakes in the Google Takeout attachment file names
so that they also can't be found in the browser view of the collection.)
I don't need to see the actual attachment file (MP3 or JPEG or whatever),
but I do need to know what its exact filename is.

You have these choices for reporting things:

- Open a pull request with a code change. 
If you do this, please limit the PR to a single thing to make it easy for me to review it.
(If you are an experienced python programmer, 
you will probably be tempted to "fix up" my clumsy style.
That's OK with me, 
but I'd rather those sorts of things came as their own PRs rather than intermingled with more substantive stuff.)
- Open an issue describing the problem.
See the GitHub repository link above.
Don't worry if you don't know exactly what's going on.
I just need enough information to figure it out.
- You can also post in the repository's discussion area.
That might be the best way to go if you are not sure you are really seeing a new problem.

## How to use this script
You want to use Python 3 to run this, 
and you may have to `pip install` some of the imported modules if you don't happen to already have them.
Even better would be to set up a python virtual environment,
and install the dependencies with `pip install -r requirements.txt`.
If you don't know what some of that means, 
contact the nearest smart alecky kid and get them to help you.

- Save sms.py in some convenient location. Let's call that location `/some/bin/sms.py`. 
It is a python script that requires Python 3.
- Use Google Takeout to download Google Voice or Google Chat messages or both. 
That will give you a file named `takeout-`_something-something_`.zip`.
- Unpack that ZIP file in some convenient location. Let's call that location `/someplace/t/`. 
- The Google Voice files will be in a directory `Takeout/Voice/Calls/`, aka `/someplace/t/Takeout/Voice/Calls/`.
- The Google Chat files will be in a directory `Takeout/Google Chat/Groups/`, aka `/someplace/t/Takeout/Google Chat/Groups/`.
- In a terminal window, go to directory `/someplace/t/Takeout/`.
- Run the python script, for example, `python /some/bin/sms.py` or `python3 /some/bin/sms.py`.
- If you get python errors, it is most likely because you are missing some of the imported modules. 
Use `pip` to install them until python stops complaining. 
- When the script starts running correctly, it will announce the locations of inputs and outputs and other helpful information.
- It can also emit warnings or TODO items.
Generally, any output lines prefixed with `>>` are just informational,
but pay attention to any output lines without that prefix.
- If the script sees problems in the information, it will report them to you.
See the information below about missing contacts.
Don't use the resulting output files until you are satisfied you have dealt with any reported problems.

### Running a test
If you would like to try this with some test data to get comfortable with things,
head down to the `test_data` subdirectory.
There are instructions there for how to use that test data with your own phone.

### Output files
The script produces four separate output files.

- an "sms" file containing a combination of SMS and MMS messages based on Google Voice
(MMS messages are used for group conversations and for messages with attachments)
- a "calls" file containing call history records
- an "sms vm" file containing MMS messages for voicemails
(The voicemail recording is included as an attachment.
If there is a transcript, it is included as a text part of the MMS message.
A voicemail also creates a "missed call" record in the "calls" file, without the recording or transcript.)
- an "sms chat" file containing a combination of SMS and MMS messages based on Google Chat

Why is there a separate file for voicemail MMS messages?
It's done that way in case you don't want to include those with the other SMS and MMS messages when you do the restore operation.
In fact you can pick and choose among any of the output files, depending on what you want to do.
SMS Backup and Restore will let you choose which files you want to use for `restore`.

### Command line options

The easiest way to use this script is as described above,
but there are optional command line arguments for changing various locations and files.
You can get the latest information about command line arguments by running the script with the single argument `-h` or `--help`.
```
usage: sms.py [-h] [-d VOICE_DIRECTORY] [-e CHAT_DIRECTORY]
              [-s SMS_BACKUP_FILENAME] [-v VM_BACKUP_FILENAME]
              [-c CALL_BACKUP_FILENAME] [-t CHAT_BACKUP_FILENAME]
              [-j CONTACTS_FILENAME] [-p {asis,configured,newest}] [-n] [-z]

Convert Google Takeout HTML and Google Chat JSON files to SMS Backup and
Restore XML files. (Version 2023-12-02 16:20)

options:
  -h, --help            show this help message and exit
  -d VOICE_DIRECTORY, --voice_directory VOICE_DIRECTORY
                        The voice_directory containing the HTML files from
                        Google Voice. Defaults to "Voice/Calls".
  -e CHAT_DIRECTORY, --chat_directory CHAT_DIRECTORY
                        The chat_directory containing the JSON files from
                        Google Chat. Defaults to "Google Chat/Groups".
  -s SMS_BACKUP_FILENAME, --sms_backup_filename SMS_BACKUP_FILENAME
                        File to receive SMS/MMS messages from Google Voice.
                        Defaults to "../sms-gvoice.xml".
  -v VM_BACKUP_FILENAME, --vm_backup_filename VM_BACKUP_FILENAME
                        File to receive voicemail MMS messages from Google
                        Voice. Defaults to "../sms-vm-gvoice.xml".
  -c CALL_BACKUP_FILENAME, --call_backup_filename CALL_BACKUP_FILENAME
                        File to receive call history records from Google
                        Voice. Defaults to "../calls-gvoice.xml".
  -t CHAT_BACKUP_FILENAME, --chat_backup_filename CHAT_BACKUP_FILENAME
                        File to receive SMS/MMS messages from Google Chat.
                        Defaults to "../sms-chat.xml".
  -j CONTACTS_FILENAME, --contacts_filename CONTACTS_FILENAME
                        JSON formatted file of definitive contact name/number
                        pairs. Defaults to "../contacts.json".
  -p {asis,configured,newest}, --number_policy {asis,configured,newest}
                        Policy for choosing the "best" number for a contact.
                        Defaults to "asis".
  -n, --nanp_numbers    Heuristically treat some partial numbers as North
                        American numbers.
  -z, --dump_data       Dump some internal tables at the end of the run, which
                        might help with sorting out some thing.

All command line arguments are optional and have reasonable defaults when the
script is run from within "Takeout/". The contacts file is optional. Output
files should be named "sms-SOMETHING.xml" or "calls-SOMETHING.xml". See the
README at https://github.com/wjcarpenter/gvoice-sms-takeout-xml for more
information.
```
When the script is printing a message for you and mentioning a file,
it gives the absolute path to the file.
That makes it a little more convenient if you want to go have a look at the file.
On the other hand, when the script is mentioning a file in an XML comment in an output file,
it might print an absolute or relative path,
depending on the value you supply (or the default) for the `--voice_directory` and `--chat_directory` arguments.
If you don't know why you'd care about the distinction,
then you probably don't care.
Relative paths in the output files are very slightly more privacy-preserving
(but only slightly).

### Missing contacts
In the Google Takeout data, 
there are some edge cases where it's impossible to figure out the contact phone number for a particular input file.
It's not too important for you to understand those edge cases,
but the script works hard to deal with them.

Two main techniques are used.
- First, the script notices name-to-number mappings as it encounters them in HTML files, 
so it might be able to figure it out automatically. 
- Second, if the script can't figure it out automatically, 
it emits a "TODO" message asking you to add an entry to a JSON file and re-run.
If you don't see any TODO messages (most people will not), then the script figured everything out.

JSON files from Google Chat don't contain phone numbers,
so any discovery of phone numbers comes from the HTML files from Google Voice.
The Google Voice files are processed first, 
so any discovered contact numbers can be used when processing the Google Chat files.
Google Chat files contain a contact name and a contact email address.
A phone number for either is sufficient, 
whether configured in the JSON contacts file or discovered in the Google Voice HTML files.

If the script didn't deal with the edge cases, 
it would be possible to see things either mapped to the number "0000000000" or without any number at all 
(which will show up as something like "Unknown caller") instead of being mapped to the correct contact.

SMS Backup and Restore is pretty good at duplicate detection during restore operations, 
but if you make a mistake and have things ending up in "0000000000" or "Unknown caller" or other strange places, 
delete those entire SMS/MMS conversations from your phone, 
fix up your run of this script, 
and restore again. 
Otherwise, a lot of MMS attachments will be detected as duplicates and will never restore properly. 
(I had 300-400 of those out of 25,000 SMS/MMS messages, and it was a big puzzle to figure it out.)

Here are some examples of the kinds of TODO messages you might see:
```
Unfortunately, we can't figure out your own phone number.
TODO: Missing +phonenumber for contact: "Me": "+",

TODO: Missing or disallowed +phonenumber for contact: "Agatha M Christie": "+",
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Agatha M Christie - Text - 2023-10-22T17_28_34Z.html"

TODO: Missing contact phone number in HTML file. Using '0000000000'.
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/ - Placed - 2013-07-29T20_56_11Z.html"

TODO:     Missing or disallowed +phonenumber for contact: "F Scott Fitzgerald": "+",
TODO: and Missing or disallowed +phonenumber for contact: "fskf@authors.example.com": "+",
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Google Chat/Groups/Space AAAAdvGdRgs/group_info.json"
```
The TODO for `Me` is a special case.
The script couldn't figure out your phone number (which it usually can do), 
so you have to provide it via that fake entry in the JSON file.
The TODO for the 3rd item above, 
where "0000000000" is used instead,
usually indicates some kind of glitch in the indicated input file.
Have a look at it. 
If it's not too important to you, probably the simplest course is to delete that input file.
Because Google Chat contacts can be resolved from either the email address or the contact name,
the last item above is an example where there is not a number for either one.
Adding a configured number to the JSON contacts file for either the email address or the name will take care of it.

If you get any of those other messages, add entries for those contacts into the JSON file.
Obviously, create that file if you haven't done so earlier.
You can probably copy and paste the end of the TODO line and just supply the missing phone number.
That will give you something like:
```
{
  "Me": "+17323210011",
  "Agatha M Christie": "+17323211111",
  "fskf@authors.example.com": "+17323215555"
}
```
Add the contact name exactly as shown in the TODO message. 
Contact names, including `Me`, are case-sensitive.
Don't forget to include the `+` and the country code with the phone number
(and no other punctuation ... just the `+` and digits). 
The order of items in that file doesn't matter, but the python JSON parser requires a comma after each item except the final one.
It also insists on the use of double quotes (not single quotes) for all of the items.
Rerun the script until you get no TODO reports about missing contact phone numbers and no other errors.

You can now use the resulting output files as a backup files to be restored with the SMS Backup and Restore app.

### Aliases and preferred numbers
The optional JSON contacts file has a simplistic mechanism for aliases for both contact names and contact numbers.
In addition to providing entries as seen in the previous section to get from a name to a number,
you can also provide an alias for a contact name with an entry like this:
```
{
  "Pelé": "Edson Arantes do Nascimento"
}
```
Likewise, you can provide an alias for a contact number with an entry like this:
```
{
  "+12123214444": "+15703214444"
}
```
The script distinguishes these from the name-to-number mappings by recognizing numbers by pattern 
(all digits with an optional leading `+`).

Finally, you can configure multiple phone numbers for a contact name by using an entry like this:
```
{
  "Edson Arantes do Nascimento": ["+17323214444", "+15703214444"]
}
```
Depending on the the number policy (described below), 
the first number in the list can be considered "preferred".
### Conflicting contact names and numbers
You might also see some informational notices about conflicting numbers for contacts.
This can happen if one of your contacts (or you) has multiple phone numbers, 
including having changed phone numbers over time.
The phone number is the thing that matters in the backup files,
so you probably don't have to do anything about these.
If you wanted to go to a lot of trouble, 
you could edit the HTML files to change the conflicting number to the one you prefer for that contact.
If you have all of the conflicting numbers in your phone contact records,
things will work out without your needing to do anything.
If you don't have one of those numbers for the contact,
then the record will show up on your phone as just the phone number and no contact name.

Why can't we just take care of this?
Well, the way things are stored on your phone is with separate
databases for contacts, messages, and calls.
We're only updating the messages and calls.
We're not touching the contacts,
so we can't add numbers to them.
It's the phone numbers in the messages and calls that tie things together.

Here is an example of this kind of informational message:
```
>> Info: conflicting information about "Edson Arantes do Nascimento": ['+17323214444'] '+15703214444'
>>    due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Edson Arantes do Nascimento - Voicemail - 2016-05-01T00_16_43Z.html"
>> Info: conflicting information about "Edson Arantes do Nascimento": ['+17323214444', '+15703214444'] '+12123214444'
>>    due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Edson Arantes do Nascimento - Voicemail - 2014-05-17T02_54_27Z.html"
```
To keep the noise down,
there will be at most one such message for any newly discovered conflicting numbers for any given contact.
In other words, for a contact with N different phone numbers in the HTML files,
you would expect to see N-1 informational messages about conflicts.
The number outside the `[brackets]` is the most recently seen number,
and the file named on the next line is where that number was first seen.

### Contact number replacement policies
If a given contact name has a single contact number,
either configured in the JSON contacts file or discovered in the HTML input files,
there is no ambiguity.
That unique number will be used for that contact throughout the output files.

In cases where there are multiple numbers for the same contact name,
you can specify what you want to do about it,
which can affect how conversations appear when you restore the backup files.
This is called the number replacement policy or simply the number policy.
Here are the possibilties:
- `asis`: (Default) When a given number is found along with that contact name, 
then that number is used in the output for that that specific case.
If the contact name is found separately from the contact number,
then the `newset` contact number will be used in the output.
- `newest`: All contact numbers for the contact name are replaced with the newest contact number,
where "newest" means appearing in an HTML file with the most recent message timestamp.
Any contact numbers mentioned in the JSON contacts file are considered to be "newer"
than any numbers discovered in HTML files.
If the contact name in the JSON file has multiple numbers,
they are assumed to be listed in reverse chronological order
(so the first one is the "newest" and will be used).
- `configured`: Similar to `asis`, 
except that only contact numbers from the JSON configuration file will be used.
Contact numbers discovered in HTML files will not be used and will generate `TODO` outputs.

Of the above policies, `asis` is the simplest to use.
`configured` is the most strict, but -- along with contact number aliases -- gives the finest control.
Here is an example of a message you might see if you use the `configured` policy but have no entry for a given contact.
The number was found in an HTML file, but it's disallowed by policy.
```
TODO: Missing or disallowed +phonenumber for contact: "Søren Aabye Kierkegaard": "+17323211414",
      due to File: "/home/wjc/git/gvoice-sms-takeout-xml/test_data/Takeout/Voice/Calls/Group Conversation - 2023-10-01T15_30_41Z.html"
```
### NANP heuristics for phone numbers
Over the years, various applications and phones have been pretty lenient with me in how my contact phone numbers are formatted.
I'm in the US, and most of my contact phone numbers are fully formed with a leading `+1` before the area code.
A few, however, have only the `+` (without the `1`),
and a few don't have the `+1` at all.
It can be tedious to create aliases for all those combinations in the contacts JSON file,
so there is a command line flag to apply "NANP heuristics" to phone numbers.
(NANP is North American Numbering Plan, which is the system used by many telephone systems in North America.)
- If there is a `+` and exactly 10 digits, the `+` is changed to `+1`.
This will be incorrect for some number of non-US phone numbers that properly include a country code other than `1`.
- If there is a `1` and exactly 10 additional digits, the `1` is changed to `+1`.
I have mixed feelings about providing this US-centric (actually, North America centric) feature.
An alternative to this would be fixing up your Google Contacts to have phone numbers with fully formatted country codes before exporting data with Google Takeout.
If you are in the middle of moving things with this script,
you could use fix up your contacts and use the heuristic when converting the data.

### Dumping runtime data
There is a command line option, `-z`, 
to have the script dump out some internal tables at the end of the run.
This can be helpful in sorting out data problems.
It can otherwise be tedious to look through various input files to try to figure out where things have gone sideways.
This info is not dumped by default because most people will not need it.
It's there as an additional concise source of information if you need it.

NOTE: The dumped data tends to use single quote marks.
If you copy and paste that into the JSON contacts file, be sure to switch them to double quote marks.
(It's not my fault.)
