# VAICOM PRO Integration

VAICOM PRO is a VoiceAttack plugin used to integrate with Digital Combat Simulator (DCS) for communicating with AI units without needing to use the F10 comms menus.

These instructions detail how to integrate Whisper server with VoiceAttack and VAICOM PRO.

**WARNING:** These instructions are a work in progress. WhisperAttack is in beta and things are subject to change.

The VAICOM PRO manual can be found on the VAICOM PRO Community Discord server.

An example VoiceAttack profile [WhisperAttack for VAICOM PRO.vap](WhisperAttack%20for%20VAICOM%20PRO.vap) is available here which is based on the default VAICOM PRO one, with updates made for Whisper support. This can be imported into VoiceAttack and used for your purposes.

## VAICOM PRO VSPX Speech Processing Mode

Within the VAICOM configuration the speech processing engine must be set to VSPX in the preferences. This is due to VoiceAttack not supporting
wildcard (`*`) characters when matching "When I say" commands when it is executed by the Whisper server. This lack of support means that there must
be an exact match on the text between wildcards. This breaks the VAICOM integration as it does not match on the full sentences that you speak.

The exported key words from the VAICOM database when run in this mode use official supported "When I say" VoiceAttack syntax that is required for Whisper.
This syntax allows for full sentences, with optional words and dynamic use of participant names etc.

## VAICOM PRO keywords database

The VAICOM PRO configuration contains an editor that can be used to add aliases for commands. WhisperAttack converts textual numbers to numerical values, e.g. "two" is 2. Because of this aliases will need to be added for keywords that contain textual numbers. For example, your wingman has the existing aliases of "two", "winger", and "bozo". You will need to add another alias for this with a value of `1`. This will need to be repeated for the other wingmen, and other items in the list of aliases shown in the editor. Refer to the VAICOM manual for instructions on how to do this.

![keywords database](./screenshots/VAICOM%20keywords%20database.png)

**NOTE:** As of VAICOM 3.0.0 support has been added so that wingmen, and other items, are already present with numerical values so do not need to be updated.

## VAICOM PRO VoiceAttack profile

The default VAICOM PRO profile that is imported into VoiceAttack requires modifications for executing the `WASC` (WhisperAttackSendCommand) plugin with the `Start Whisper Recording` or `Stop Whisper Recording` Plugin Context value when TX buttons are pressed and released.

### Disable speech recognition

You need to disable speech recognition in VoiceAttack so that only the Whisper transcribed commands are used. If you do not do so then you get duplicate commands issued, once for the normal Windows speech recognition engine, and then a second one from the Whisper transcribed text that is sent to VA. This requires a restart of VoiceAttack and you should now see the message stating voice recognition is disabled.

### Run command for each TX button

For each of the TX button press and release commands you need to add an associated `Execute external plugin` action for the WhisperAttack `WASC` plugin. See the README for instructions on installing this plugin into VoiceAttack.

- Open each Push-To-Talk button command
- Go to **Other > Advanced > Execute and External Plugin Function** and select the `WASC` plugin from the Plugin dropdown
- The **Plugin Context** for press buttons need a value of `Start Whisper Recording` and for release buttons this needs a value of `Stop Whisper Recording`
- Select the added action and click **Up** so that this occurs first in the sequence

![Add run application to push to talk](./screenshots/Add%20execute%20plugin%20to%20push%20to%20talk.png)

This needs to be done for all TX buttons in use.

![Start and stop on all tx buttons](./screenshots/Start%20and%20stop%20on%20all%20tx%20buttons.png)


## Testing VAICOM integration

Start the WhisperAttack server, VAICOM PRO, then start DCS and jump into an instant action mission for testing. Turn on your plane's battery and radio and then use the correct TX button for the relevant radio. For example, requesting startup from the ATC. You may need to issue one press/release with "ATC Select" to select the recipient, and then another press/release for "Request startup".

As per the VAICOM documentation when participants are used in the voice command when using the VSPX mode then they should be said with no pauses. For example, "ATC request startup". When using WhisperAttack this would also be required as it says the full sentence in one go, with no pause between participant and command, hence does not wait for an acknoledgement of the participant prior to issuing the command.

You should see the following occur:
1. The whisper server transcribe your spoken words to text and sends them to VoiceAttack
1. VoiceAttack locate the correct "When I say" command and send it to VAICOM
1. The associated radio command made in DCS

![WhisperAttack UI and VoiceAttack](./screenshots/WhisperAttack%20UI%20and%20VoiceAttack.png)

## Importing VAICOM F10 menu items

The VAICOM database is automatically updated with items from the F10 menu, if you have enabled this option in the VAICOM settings. These items are exported to the clipboard and `keywords.csv` file with a prefix of `Action` when clicking Finish in VAICOM, or performing an export. The keywords can be used to update your VoiceAttack profile. This however does not happen when using the VSPX mode in VAICOM, only when not using VSPX. Whilst these aree exported to the `keywords.csv` file they are not put in the clipboard or `keywords.txt` file so you cannot automatically update your VoiceAttack profile with those. This can be solved using the below manual steps to add these yourself.

Perform an Export from the VAICOM editor and the `keywords.csv` file will be created in your `VoiceAttack\apps\VAICOMPRO\Export` directory. As per the screenshot below these appear under the `;Imported F10 menu commands;` heading.

![Vaicom CSV keywords](./screenshots/Vaicom%20CSV%20keywords.png)

For each of these lines copy the blue text, including the semicolon `;` character, and paste them into a file in single line. For example:

```
Action Bogey Dope; Action Request Picture; Friendly Picture; Action Load Recon;
```

Next you will need to add this to the end of the keywords collection in your VoiceAttack profile. For example, if the current keywords collection ends in:

```
Server; Mystery; Mission;
```

then after pasting this in it would be:

```
Server; Mystery; Mission; Action Bogey Dope; Action Request Picture; Friendly Picture; Action Load Recon;
```

You can then save this update to the VoiceAttack profile.

**Note** If you update your VAICOM database, e.g. after reseting it and clicking Finish, and then copy the keywords from the clipboard to your VoiceAttack profile the F10 menu items would be lost. This is due to VAICOM not exporting those for VSPX. You will need to reapply those to the end of the keywords collection again.

Hopefully in the future VAICOM will export those in the same way it does for the non-VSPX mode so that these manual steps are no longer necessary.