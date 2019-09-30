# Weatherbot

This is a Chatbot project. The goal of this project is to enable chatbot to communicate with users using natural language. This weatherbot could help people to search the weather of some cities or places all around world and get a brief information about the weather as feedback.

## Getting Started

Build a telegram bot by talking to [*BotFather*](https://telegram.me/BotFather) and input **/newbot** and then follow the steps it ask to create new bot. Afterthat, copy your token and replace the TOKEN string in chatbotMain.py, line 22. [*Here is a introduction for BotFather.*](https://core.telegram.org/bots#6-botfather)

### Environments
Install Python 3.7 with Anaconda and then use conda to create a virtual environment clone from base as:
```
conda create --name myclone --clone base
```
Replace myclone with the name of the new environment.
Then use conda to active the new environment and install packages under new environment:
```
conda activate myenv
```
Replace myenv with the name of the new environment.

### Installation
Please install all of the additional packages under new environment.

Install spacy with midsize English Models:
```
pip install -U spacy
python -m spacy download en_core_web_md
```
Install rasa-nlu:
```
pip install rasa-nlu
```
Install pycountry:
```
pip install pycountry
```

## Usage example

After create the new bot on telegram and replace the new token in the chatbotMain.py, simply run the chatbotMain.py and wait for a few minutes to let the program trainning a new rasa_nlu model. Then chat with it.

**Please input correct city and country names, the program is not able to recognize the place with incorrect names.**
**When you want to search with latitude an longitude, please separate the negative sign with numbers in order to get correct value.**
**The search by zipcode usage is only available for US postal code, the program connot recgonize other countries' postal codes.**
