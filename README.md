# gvoice-sms-takeout-xml
Convert Google Voice SMS data from Takeout to .xml suitable for use with SMS Backup and Restore

This is a personal project from a few years back when Google switched Voice to Hangouts and I wanted to grab my old messages and get them into a usable format. It worked at the time; I don't know if it works as-is, but I'm planning on some testing in the near term to get it functional. 

Input data is a folder of SMS .html files from Google Takeout.

# This fork
This fork of the repository corrects several problems I ran into when using the original script.
You want to use python3 to run this, and you may have to "pip install" some of the imported modules if you don't happen to already have them.

Two techniques are used to deal with the several edge cases where it's impossible to figure out the contact phone number for an SMS/MMS. First, we notice name to number mappings as we encounter them along the way, so we might be able to figure it out automatically. Second, if we can't figure it out, we emit a message asking the user to add an entry to a JSON file and re-run until everything is accounted for.

If we didn't deal with those edge cases, it would be possible to see SMS/MMS messages either mapped to the number "0" or without any number at all (which will show up as something like "Unknown caller") instead of being mapped to the correct contact.

SMS Backup and Restore is pretty good at duplicate detection, but if you make a mistake and have things ending up in "0" or "Unknown caller", delete those entire SMS/MMS conversations from your phone, fix up your run of this script, and restore again. Otherwise, a lot of MMS attachments will be detected as duplicates and will never restore properly. (I had 300-400 of those out of 25,000 SMS/MMS messages, and it was a big puzzle to figure it out.)
