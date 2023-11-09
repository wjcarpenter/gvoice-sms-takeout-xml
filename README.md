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

## Data examples
These snippets of data are slightly trimmed down and "pretty formatted" examples
from either the Google Takeout HTML files or the SMS Backup and Restore back up files.
You don't need to look at any of this to use the script.
This is mostly put here for my own reference as I worked through cases.
It is not a complete set of all the possible variants.

### A single text SMS (from Takeout)
```
<html>
<head>
<title>Susie Glow</title>
</head>
<body>
  <div class="hChatLog hfeed">
    <div class="message">
      <abbr class="dt" title="2023-09-01T19:29:20.270-07:00">Sep 1, 2023, 7:29:20&#8239;PM Pacific Time</abbr>:
        <cite class="sender vcard">
          <a class="tel" href="tel:+18885554321">
            <span class="fn">Susie Glow</span>
          </a>
        </cite>:
      <q>What is your favorite color?</q>
    </div>

    <div class="message">
      <abbr class="dt" title="2023-09-01T20:27:36.727-07:00">Sep 1, 2023, 8:27:36&#8239;PM Pacific Time</abbr>:
        <cite class="sender vcard">
          <a class="tel" href="tel:+441234567890">
            <abbr class="fn" title="">Me</abbr>
          </a>
        </cite>:
      <q>Oh, I cannot decide</q>
    </div>
  </div>

  <div class="tags">Labels:
    <a rel="tag" href="http://www.google.com/voice#sms">Text</a>,
    <a rel="tag" href="http://www.google.com/voice#inbox">Inbox</a>
  </div>
  <div class="deletedStatusContainer">User Deleted: False</div>
</body>
</html>
```
### A group message with an image attachment, one user not in contacts (from Takeout)
```
<html>
<head>
<title>Group Conversation</title>
</head>
<body>
  <div class="hChatLog hfeed">
    <div class="participants">Group conversation with:
      <cite class="sender vcard">
        <a class="tel" href="tel:+18885551234">
          <span class="fn">Joe Blow</span>
        </a>
      </cite>,
      <cite class="sender vcard">
        <a class="tel" href="tel:+17738446228">
          <span class="fn">+17735559876</span>
        </a>
      </cite>
      <cite class="sender vcard">
        <a class="tel" href="tel:+18885554321">
          <span class="fn">Susie Glow</span>
        </a>
      </cite>
    </div>

    <div class="message">
      <abbr class="dt" title="2023-10-01T08:30:41.563-07:00">Oct 1, 2023, 8:30:41&#8239;AM Pacific Time</abbr>:
      <cite class="sender vcard">
        <a class="tel" href="tel:+18885554321">
          <span class="fn">Susie Glow</span>
        </a>
      </cite>:
      <q>Do you like my hat?</q>
    </div>

    <div class="message">
      <abbr class="dt" title="2023-10-01T11:44:12.570-07:00">Oct 1, 2023, 11:44:12&#8239;AM Pacific Time</abbr>:
      <cite class="sender vcard">
        <a class="tel" href="tel:+441234567890">
          <abbr class="fn" title="">Me</abbr>
        </a>
      </cite>:
      <q>I do. I do like your hat. Here's a picture.</q>
      <div>
        <img src="Group Conversation - 2023-10-01T15_30_41Z-2-1" alt="Image MMS Attachment" />
      </div>
    </div>
  </div>

  <div class="tags">Labels:
    <a rel="tag" href="http://www.google.com/voice#sms">Text</a>,
    <a rel="tag" href="http://www.google.com/voice#inbox">Inbox</a>
  </div>
  <div class="deletedStatusContainer">User Deleted: False</div>
</body>
</html>
```
### A vcard attachment (from Takeout)
```
<div class="message">
  <abbr class="dt" title="2021-07-13T14:27:27.996-07:00">Jul 13, 2021, 2:27:27&#8239;PM Pacific Time</abbr>:
  <cite class="sender vcard">
    <a class="tel" href="tel:+18885554321">
      <span class="fn">Susie Glow</span>
    </a>
  </cite>:
  <q>That person I told you about.</q>
  <div>
    <a class="vcard" href="Group Conversation - 2021-07-13T21_25_26Z-3-1">Contact card attachment</a>
  </div>
</div>
```
### A vcard attachment (from a backup file)
```
<part
  seq="0"
  ct="text/x-vCard"
  name="null"
  chset="null"
  cd="null"
  fn="null"
  cid="&lt;contact000000&gt;"
  cl="contact000000.vcf"
  ctt_s="null"
  ctt_t="null"
  text="null"
  sub_id="1"
  data="QkV ... A0K"
/>
```
### A received SMS (from a backup file)
```
<sms
  protocol="0"
  address="+18885554321"
  date="1696889179789"
  type="1"
  subject="null"
  body="That's about right."
  toa="null"
  sc_toa="null"
  service_center="+14054720055"
  read="1"
  status="-1"
  locked="0"
  date_sent="1696889176000"
  sub_id="1"
  readable_date="Oct 9, 2023 15:06:19"
  contact_name="Susie Glow"
/>
```
### A sent SMS (from a backup file)
```
<sms
  protocol="0"
  address="+18885554321"
  date="1696889247396"
  type="2"
  subject="null"
  body="I thought so."
  toa="null"
  sc_toa="null"
  service_center="null"
  read="1"
  status="-1"
  locked="0"
  date_sent="0"
  sub_id="1"
  readable_date="Oct 9, 2023 15:07:27"
  contact_name="Susie Glow"
/>
```
### A sent group MMS with an image attachment (from a backup file)
```
<mms
  date="1696900308000"
  rr="129"
  sub="null"
  ct_t="application/vnd.wap.multipart.related"
  read_status="null"
  seen="1"
  msg_box="2"
  address="+18885551234~18885554321"
  sub_cs="null"
  resp_st="128"
  retr_st="null"
  d_tm="null"
  text_only="0"
  exp="604800"
  locked="0"
  m_id="mavodi-1-88-a4-4-7e-656356bc-ad1b4253909"
  st="null"
  retr_txt_cs="null"
  retr_txt="null"
  creator="com.google.android.apps.messaging"
  date_sent="0"
  read="1"
  m_size="15789"
  rpt_a="null"
  ct_cls="null"
  pri="129"
  sub_id="1"
  tr_id="T18b1723de77"
  resp_txt="null"
  ct_l="null"
  m_cls="personal"
  d_rpt="129"
  v="18"
  _id="50"
  m_type="128"
  readable_date="Oct 9, 2023 18:11:48"
  contact_name="Joe Blow, Susie Glow"
>
  <parts>
    <part
      seq="-1"
      ct="application/smil"
      name="null"
      chset="null"
      cd="null"
      fn="null"
      cid="&lt;smil&gt;"
      cl="smil.xml"
      ctt_s="null"
      ctt_t="null"
      text='&lt;smil&gt;&lt;head&gt;&lt;layout&gt;&lt;root-layout/&gt;&lt;region id="Image" fit="meet" top="0" left="0" height="80%" width="100%"/&gt;&lt;region id="Text" top="80%" left="0" height="20%" width="100%"/&gt;&lt;/layout&gt;&lt;/head&gt;&lt;body&gt;&lt;par dur="5000ms"&gt;&lt;img src="Sloth in bowl saying meh" region="Image" /&gt;&lt;/par&gt;&lt;par dur="5000ms"&gt;&lt;text src="text000002.txt" region="Text" /&gt;&lt;/par&gt;&lt;/body&gt;&lt;/smil&gt;'
      sub_id="1"
    />
    <part
      seq="0"
      ct="image/png"
      name="null"
      chset="null"
      cd="null"
      fn="null"
      cid="&lt;Sloth in bowl saying meh&gt;"
      cl="Sloth in bowl saying meh"
      ctt_s="null"
      ctt_t="null"
      text="null"
      sub_id="1"
      data="iVBORw0 ... 4fGxsfGhohHR"
    />
    <part
      seq="0"
      ct="text/plain"
      name="null"
      chset="106"
      cd="null"
      fn="null"
      cid="&lt;text000002&gt;"
      cl="text000002.txt"
      ctt_s="null"
      ctt_t="null"
      text="This is a sloth."
      sub_id="1"
    />
  </parts>
  <addrs>
    <addr address="+441234567890" type="137" charset="106" />
    <addr address="+18885551234" type="151" charset="106" />
    <addr address="+18885554321" type="151" charset="106" />
  </addrs>
</mms>
```
### The decoded SMIL text for the above MMS
```
<smil>
  <head>
    <layout>
      <root-layout/>
      <region
        id="Image"
        fit="meet"
        top="0"
        left="0"
        height="80%"
        width="100%"
      />
      <region
        id="Text"
        top="80%"
        left="0"
        height="20%"
        width="100%"
      />
    </layout>
  </head>
  <body>
    <par dur="5000ms">
      <img src="Sloth in bowl saying meh" region="Image" />
    </par>
    <par dur="5000ms">
      <text src="text000002.txt" region="Text" />
    </par>
  </body>
</smil>
```
### A voicemail (from Takeout)
```
<html>
<head>
<title>Voicemail from Susie Glow</title>
<style> </style>
</head>
<body>
  <div class="haudio">
    <span class="album">Call Log for</span>
    <span class="fn">Voicemail from Susie Glow</span>
    <div class="contributor vcard">Voicemail from
      <a class="tel" href="tel:+18885554321">
        <span class="fn">Susie Glow</span>
      </a>
    </div>
    <abbr class="published" title="2014-05-16T19:54:27.000-07:00">May 16, 2023, 7:54:27&#8239;PM Pacific Time</abbr>
Transcript: ...
    <br />
    <audio controls="controls" src="Susie Glow - Voicemail - 2023-05-17T02_54_27Z.mp3">
      <a rel="enclosure" href="Susie Glow - Voicemail - 2023-05-17T02_54_27Z.mp3">Audio</a>
    </audio>
    <abbr class="duration" title="PT22S">(00:00:22)</abbr>

    <div class="tags">Labels:
      <a rel="tag" href="http://www.google.com/voice#inbox">Inbox</a>,
      <a rel="tag" href="http://www.google.com/voice#voicemail">Voicemail</a>
    </div>
    <div class="deletedStatusContainer">User Deleted: False</div>
  </div>
</body>
</html>

<html>
<head>
<title>Recorded call with Susie Glow</title>
</head>
<body>
  <div class="haudio">
    <span class="album">Call Log for</span>
    <span class="fn">Recorded call with Susie Glow</span>
    <div class="contributor vcard">Recorded call with
      <a class="tel" href="tel:+18885554321">
        <span class="fn">Susie Glow</span>
      </a>
    </div>
    <abbr class="published" title="2019-05-22T11:18:56.616-07:00">May 22, 2019, 11:18:56&#8239;AM Pacific Time</abbr>

    <audio controls="controls" src="Susie Glow - Recorded - 2019-05-22T18_18_56Z.mp3">
      <a rel="enclosure" href="Susie Glow - Recorded - 2019-05-22T18_18_56Z.mp3">Audio</a>
    </audio>
    <abbr class="duration" title="PT29M46S">(00:29:46)</abbr>

    <div class="tags">Labels:
      <a rel="tag" href="http://www.google.com/voice#recorded">Recorded</a>,
      <a rel="tag" href="http://www.google.com/voice#inbox">Inbox</a>,
      <a rel="tag" href="http://www.google.com/voice#unread">Unread</a>
    </div>
    <div class="deletedStatusContainer">User Deleted: False</div>
  </div>
</body>
</html>
```
### An incoming call (from Takeout)
```
<html>
<head>
<title>Received call from</title>
</head>
<body>
  <div class="haudio">
    <span class="album">Call Log for </span>
    <span class="fn">Received call from </span>
    <div class="contributor vcard">Received call from
      <a class="tel" href="tel:+17738446228">
        <span class="fn"></span>
      </a>
    </div>
    <abbr class="published" title="2016-11-22T14:27:58.000-08:00">Nov 22, 2016, 2:27:58&#8239;PM Pacific Time</abbr>
    <abbr class="duration" title="PT4S">(00:00:04)</abbr>

    <div class="tags">Labels:
      <a rel="tag" href="http://www.google.com/voice#received">Received</a>
    </div>
    <div class="deletedStatusContainer">User Deleted: False</div>
  </div>
</body>
</html>

<html>
<head>
<title>Placed call to Joe Blow</title>
</head>
<body>
  <div class="haudio">
    <span class="album">Call Log for</span>
    <span class="fn">Placed call to Joe Blow</span>
    <div class="contributor vcard">Placed call to
      <a class="tel" href="tel:+18885551234">
        <span class="fn">Joe Blow</span>
      </a>
    </div>
    <abbr class="published" title="2021-06-07T14:10:27.000-07:00">Jun 7, 2021, 2:10:27&#8239;PM Pacific Time</abbr>
    <abbr class="duration" title="PT2M27S">(00:02:27)</abbr>

    <div class="tags">Labels:
      <a rel="tag" href="http://www.google.com/voice#placed">Placed</a>
    </div>
    <div class="deletedStatusContainer">User Deleted: False</div>
  </div>
</body>
</html>
```
### An incoming call (from a backup file)
```
<call
  number="18885551234"
  duration="72"
  date="1521088688853"
  type="2"
  presentation="1"
  subscription_id="null"
  post_dial_digits=""
  subscription_component_name="null"
  readable_date="Mar 14, 2018 21:38:08"
  contact_name="Joe Blow"
/>
```
### An outgoing call (from a backup file)
```
<call
  number="17738446228"
  duration="0"
  date="1521654952742"
  type="3"
  presentation="1"
  subscription_id="null"
  post_dial_digits=""
  subscription_component_name="null"
  readable_date="Mar 21, 2018 10:55:52"
  contact_name="(Unknown)"
/>
```
