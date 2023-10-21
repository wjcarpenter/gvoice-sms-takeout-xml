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

# HOW TO USE THIS SCRIPT

- Save sms.py in some convenient location. Let's call that location `/some/bin/sms.py`. It is a python script that requires Python 3.
- Use Google Takeout to download Google Voice messages. That will give you a file named `takeout-`_something-something_`.zip`.
- Unpack that ZIP file in some convenient location. Let's call that location `/someplace/t/`. The Google Voice files will be in a directory `Takeout/Voice/Calls/`, aka `/someplace/t/Takeout/Voice/Calls/`.
- Create a text file in JSON format at `/someplace/t/contacts.json` with one entry:
```
{
  ".me": "+441234567890"
}
```
- Change the phone number in that `.me` entry to your own phone number. Include the `+` and your country code. No other punctuation.
- In a terminal window, go to directory `/someplace/t/Takeout/Voice/Calls/`.
- Run the python script, for example, `python /some/bin/sms.py` or `python3 /some/bin/sms.py`.
- If you get python errors, it is most likely because you are missing some of the imported modules. Use PIP to install them until python stops complaining. For example, `pip install bs4`.
- When the script starts running correctly, it will announce the locations of inputs and outputs and other helpful information.
- It is as likely as not that you will have some SMS/MMS messages for which the script cannot figure out the contact phone number. That's because of the Takeout format. The script tries hard, but if it can't figure it out, it tells you with messages like this:
```
../../../contacts.json: TODO: add a +phonenumber for contact: "Joe Blow": "+",
../../../contacts.json: TODO: add a +phonenumber for contact: "Susie Glow": "+",
```
- If you get any of those messages, add entries for those contacts into the JSON file. That will give you something like:
```
{
  ".me": "+441234567890",
  "Susie Glow": "+18885554321",
  "Joe Blow": "+18885551234"
}
```
- Add the contact name exactly as shown in the warning message. Don't forget to include the `+` and the country code with the phone number. The order of items in that file doesn't matter, but the python JSON parser requires a comma after each item except the final one.
- Rerun the script until you get no errors and no warnings about missing contact phone numbers.
- You can now use the resulting output file as a backup file to be restored with the SMS Backup and Restore app (https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore)
