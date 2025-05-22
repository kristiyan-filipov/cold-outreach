# Cold outreach
A Python application that gets the last n number of emails from an inbox, determines if they're a cold outreach email and uploads them to monday.com along with any attachments.

# Setup
You need your own API keys for OpenAI and monday.com, as well as a credentials file for a Google Cloud project, that should be called "credentials.json" and placed in the same directory as the program.
The monday.com API key should be from an account that has access to the board that you want to upload to.

All of the IDs and API keys will be stored inside of a config.json file, if you want to change them simply open the file and change the values, or delete it to be prompted to input them again.

# Usage
Put in your credentials.json file in the directory, put in your access tokens when prompted. Log into the google account you want to fetch the emails from. Input how many of the last emails in your inbox you want to check, and done! Any attachments downloaded will also be saved to a folder called "attachments".

# Installation
Download the version appropriate for your operating system in [releases](https://github.com/kristiyan-filipov/cold-outreach/releases), and simply open it.

# Getting monday.com API key and IDs
In order to get the board ID, group ID and API key for monday.com, you need to do the following:
Getting your board ID:
1. Log into monday.com
2. Go to the board you wish to upload to
3. Copy the ID of the board from the URL. (The number after "/boards/")

Next to get your token and group ID:
1. Click on your profile
2. Go to "Developers"
3. Copy your token from the "My access tokens" section.

And lastly for your group ID:
1. Again from "Developers", go to the "API playground" section
2. Paste and run this code, but replace the 123456789 with your board ID:
{
  boards(ids: 123456789) {
    name
    groups {
      id
      title
    }
  }
}
3. You should now get a response containing all of the groups in your board, copy the ID of the group you want to upload to.

