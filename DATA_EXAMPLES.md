# Data examples
These snippets of data are slightly trimmed down and "pretty formatted" examples
from either the Google Takeout HTML files or the SMS Backup and Restore back up files.
You don't need to look at any of this to use the script.
This is mostly put here for my own reference as I worked through cases.
It is not a complete set of all the possible variants.

## A single text SMS (from Takeout)
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
## A group message with an image attachment, one user not in contacts (from Takeout)
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
## A vcard attachment (from Takeout)
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
## A vcard attachment (from a backup file)
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
## A received SMS (from a backup file)
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
## A sent SMS (from a backup file)
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
## A sent group MMS with an image attachment (from a backup file)
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
## The decoded SMIL text for the above MMS
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
## A voicemail (from Takeout)
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
## An incoming call (from Takeout)
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
## An incoming call (from a backup file)
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
## An outgoing call (from a backup file)
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
## A group_info file (from Google Takeout for Google Chat)
```
{
  "members": [
    {
      "name": "Alan A Milne",
      "email": "aamilne@authors.example.com",
      "user_type": "Human"
    },
    {
      "name": "Maria S Curie",
      "email": "mssc@science.example.org",
      "user_type": "Human"
    }
  ]
}
```
## A text message (from messages.json in Google Takeout for Google Chat)
```
    {
      "creator": {
        "name": "Maria S Curie",
        "email": "mssc@science.example.org",
        "user_type": "Human"
      },
      "created_date": "Wednesday, April 15, 2015 at 12:51:41 AM UTC",
      "text": "I\u0027ve heard of polymaths, but I think you might be the first demi-math",
      "topic_id": "beJ6uN-Eb_A",
      "message_id": "1pRI-QAAAAE/beJ6uN-Eb_A/beJ6uN-Eb_A"
    },
```
## A JPEG attachment message (from messages.json in Google Takeout for Google Chat)
```
    {
      "creator": {
        "name": "Alan A Milne",
        "email": "aamilne@authors.example.com",
        "user_type": "Human"
      },
      "created_date": "Monday, April 27, 2015 at 8:29:01 PM UTC",
      "attached_files": [
        {
          "original_name": "2015-04-27.jpg",
          "export_name": "File-2015-04-27.jpg"
        }
      ],
      "topic_id": "N-9_2Qw6DvE",
      "message_id": "1pRI-QAAAAE/N-9_2Qw6DvE/N-9_2Qw6DvE"
    },
```