# gvoice-sms-takeout-xml
Convert Google Voice data from Google Takeout to XML files suitable for use with SMS Backup and Restore.

Google Takeout, 
<https://takeout.google.com>,
is a tool provided by Google for downloading various kinds of data associated with your Google account.
In this case, it's data from Google Voice.
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
The idea is that you then use those XML files to do a "restore" with the app.
That transfers your Google Voice history into your phones native history.

## This fork
This is a fork of <https://github.com/karlrees/gvoice-sms-takeout-xml>,
which is itself a fork of <https://github.com/calyptecc/gvoice-sms-takeout-xml>.
Although I have made a massive number of changes, 
so that it does not look much like the originals any more (perhaps it's not even recognizable),
I have kept the same repo name and script name for the sake of being easily found.

This fork corrects several problems I ran into when using the original scripts.
I also added some significant additional features.

### Apologia
Reverse engineering is a hazardous business.
There are already many special cases and oddities dealt with by the script.
There are undoubtedly more that I either didn't happen to encounter, 
or that I didn't notice.
Google could at any time change the format of the Google Takeout files, 
or (less likely) SMS Backup and Restore could change the requirements for backup files.
I welcome you bringing additional things like that to my attention,
though fixing them up is the usual freebie "best effort" sort of thing.
Undoubtedly, after some months or years, 
I'll myself become a little hazy on the workings of the script,
and that might add some time.

The best evidence to give is the original HTML file that provokes the issue.
The script usually names a specific file that gives it a headache,
but sometimes it will not know that it's misbehaving, 
in which case you have a little detective work to do.
In the XML outputs, input file names are includes as XML comments.
For the case of being unable to find referenced attachments,
it's probably some new quirk of the trial and error way the script has of figuring it out.
I don't need to see the actual attachment file (MP3 or JPEG or whatever),
but I do need to know what it's filename is.

You have these choices for reporting things:

- Open a pull request with a code change. 
If you do this, please limit the PR to a single thing to make it easy for me to review it.
(If you are an experienced python programmer, 
you will probably be tempted to "fix up" my clumsy style.
That's OK with me, 
but I'd rather those sorts of things come as their own PRs rather than intermingled with more substantive stuff.)
- Open an issue describing the problem.
Don't worry if you don't know exactly what's going on.
I just need enough information to figure it out.
- You can also post in this repository's discussion area.
That might be the best way to go if you are not sure you are really seeing a new problem.

## How to use this script
You want to use python3 to run this, 
and you may have to "pip install" some of the imported modules if you don't happen to already have them.
If you don't know what any of that means, 
contact the nearest smart aleck kid and get them to help you.

- Save sms.py in some convenient location. Let's call that location `/some/bin/sms.py`. It is a python script that requires Python 3.
- Use Google Takeout to download Google Voice messages. That will give you a file named `takeout-`_something-something_`.zip`.
- Unpack that ZIP file in some convenient location. Let's call that location `/someplace/t/`. 
The Google Voice files will be in a directory `Takeout/Voice/Calls/`, aka `/someplace/t/Takeout/Voice/Calls/`.
- In a terminal window, go to directory `/someplace/t/Takeout/Voice/Calls/`.
- Run the python script, for example, `python /some/bin/sms.py` or `python3 /some/bin/sms.py`.
- If you get python errors, it is most likely because you are missing some of the imported modules. 
Use PIP to install them until python stops complaining. 
For example, `pip install bs4`.
- When the script starts running correctly, it will announce the locations of inputs and outputs and other helpful information.

### Output files
The script produces three separate output files.

- an "sms" file containing a combination SMS and MMS messages
(MMS messages are used for group conversations and for messages with attachments.)
- a "calls" file containing call history records
- an "sms vm" file containing MMS messages for voicemails
(The voicemail recording is included as an attachment.
If there is a transcript, it is included as a text part of the MMS message.
A voicemail also creates a record in the "calls" file, without the recording or transcript.)

### Command line options

### Missing and conflicting contacts
In the Google Takeout data, there are some edge cases where it's impossible to figure out the contact phone number.
It's not too important for you to understand those edge cases,
but the script works hard to deal with them.
Two main techniques are used.
First, we notice name to number mappings as we encounter them along the way, so we might be able to figure it out automatically. 
For anything that can't be resolved when the file is first read, we save it for a second pass, hoping that we figure it out from a later file.
For those kinds of files, you'll first see a message that processing was "Deferred",
and then later a message that a "2nd pass" is being attempted.
Second, if we can't figure it out by that second pass, we emit a message asking the user to add an entry to a JSON file and re-run.
If you see those deferred and second pass messages, 
you don't have to worry about them unless there is a "TODO" message telling you to add a contact number to the JSON file.
If you don't see any TODO messages (most people will not), then the script figured everything out.

If we didn't deal with the edge cases, 
it would be possible to see things either mapped to the number "0" or without any number at all 
(which will show up as something like "Unknown caller") instead of being mapped to the correct contact.

SMS Backup and Restore is pretty good at duplicate detection, 
but if you make a mistake and have things ending up in "0" or "Unknown caller" or other strange places, 
delete those entire SMS/MMS conversations from your phone, 
fix up your run of this script, 
and restore again. 
Otherwise, a lot of MMS attachments will be detected as duplicates and will never restore properly. 
(I had 300-400 of those out of 25,000 SMS/MMS messages, and it was a big puzzle to figure it out.)

Here are some examples of the kinds of TODO messages you might see:
```
Unfortunately, we can't figure out your own phone number.
TODO: /home/wjc/t/contacts.json: add a +phonenumber for contact: "me": "+",

TODO: /home/wjc/t/contacts.json: add a +phonenumber for contact: "Joe Blow": "+",
      due to File: "/home/wjc/t/Takeout/Voice/Calls/Joe Blow - Text - 2023-10-22T17_28_34Z.html"

TODO: /home/wjc/t/contacts.json: add a +phonenumber for contact: "Susie Glow": "+",
      due to File: "/home/wjc/t/Takeout/Voice/Calls/Susie Glow - Text - 2023-10-22T17_28_34Z.html"
```
The TODO for `me` is a special case.
The script couldn't figure out your phone number, so you have to provide it via that fake entry in the JSON file.

If you get any of those messages, add entries for those contacts into the JSON file.
You can probably copy and paste the end of the TODO line and just supply the missing phone number.
Obviously, create that file if you haven't done so earlier.
That will give you something like:
```
{
  "me": "+441234567890",
  "Susie Glow": "+18885554321",
  "Joe Blow": "+18885551234"
}
```
Add the contact name exactly as shown in the TODO message. 
Don't forget to include the `+` and the country code with the phone number. 
The order of items in that file doesn't matter, but the python JSON parser requires a comma after each item except the final one.
Rerun the script until you get no errors and no warnings about missing contact phone numbers.

You can now use the resulting output file as a backup file to be restored with the SMS Backup and Restore app.

You might also see some informational notices about conflicting numbers for contacts.
This can happen if one of your contacts has multiple phone numbers, 
including having changed phone numbers over time.
The phone number is the thing that matters in the backup files,
so you probably don't have to do anything about these.
If you wanted to go to a lot of trouble, 
you could edit the HTML files to change the conflicting number to the one you prefer for that contact.
If you have all of the conflicting numbers in your phone contact records,
things will work out without your needing to do anything.

Here is an example of this kind of informational message:
```
>> Info: conflicting information about "Joe Blow": +14255552222 {'+12065551111'}
>>    due to File: "/home/wjc/t/Takeout/Voice/Calls/Joe Blow - 2017-12-03T00_39_16Z.html"
>> Info: conflicting information about "Joe Blow": +18885551234 {'+12065551111', '+14255552222'}
>>    due to File: "/home/wjc/t/Takeout/Voice/Calls/Joe Blow - Placed - 2023-09-26T20_48_32Z.html"
>> Info: conflicting information about "Susie Glow": +18885554321 {'+12125553333'}
>>    due to File: "/home/wjc/t/Takeout/Voice/Calls/Susie Glow - Received - 2014-12-19T01_30_10Z.html"
```
To keep the noise down,
there will be at most one such message for any newly discovered conflicting numbers for any given contact.
In other words, for a contact with N different phone numbers in the HTML files,
you would expect to see N-1 informational messages about conflicts.
The number outside the `{braces}` is the most recently seen number,
and the file named on the next line is where that number was first seen.
The script will sometimes need to find a contact's phone number from the contact name.
In cases of conflicts, the most recently seen number will be used.
(That's known in some circles as "last writer wins".)
