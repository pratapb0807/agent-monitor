from apscheduler.schedulers.blocking import BlockingScheduler
import requests
import os
import logging
import json
import urllib.request
from bs4 import BeautifulSoup as soup

logging.basicConfig(level=logging.INFO)

#agents u want to check in format location_in_speedcurve:agent_region
regions = {'salesforce-01':'Virginia, US', 'salesforce-02':'Sydney, APAC'}


#slack webhook
SLACK_WEBHOOK='https://hooks.slack.com/services/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'

#read mailgun variables
DOMAIN_NAME=os.environ.get('MAILGUN_DOMAIN')
API_KEY=os.environ.get('MAILGUN_API_KEY')

#recipients who get the alert mail
EMAIL_RECIPIENT="bpratap@salesforce.com"

#url to scrape
url = 'https://wpt1.speedcurve.com/getTesters.php'
req = urllib.request.Request(url , headers={'User-Agent': 'Mozilla/5.0'})

sched = BlockingScheduler()

#check if any agent is active is active for a region
def check_active(loc):
    for agent in loc.find_all("tester"):
        if int(agent.elapsed.text) <= 2:
            return True
    return False

def send_mail_alert(agent_loc, agent_region):
    return requests.post(
        "https://api.mailgun.net/v3/"+DOMAIN_NAME+"/messages",
        auth=("api", API_KEY),
        data={"from": "<mailgun@"+DOMAIN_NAME+">",
              "to": [EMAIL_RECIPIENT],
              "subject": "ALERT!! No agent active in "+agent_region+".",
              "text": "Unable to find any active agent in "+agent_region+" region.\n The error is generated when last check-in to speedcurve exceeds 2 min for all agents corresponding to the region.\n This error can be result of APP CRASH of the agent attached to that region or a new deploy under progress.\n Please keep atleast one agent active for each region.\n The name of location for this region is \'"+agent_loc+"\' go to http://wpt1.speedcurve.com/getTesters.php and search the location on the page for any further info."
                      "\n"
                      "\n"
                      "Thank You."
              })

def send_slack_alert(agent_loc, agent_region):
    headers = {
    'Content-type': 'application/json',
    }
    msg_data = "Unable to find any active agent in "+agent_region+" region. The error is generated when last check-in to speedcurve exceeds 2 min for all agents corresponding to the region. The name of location for this region is \'"+agent_loc+"\' go to http://wpt1.speedcurve.com/getTesters.php and search the location on the page for any further info."
    text_data = '{"text":"'+msg_data+'"}'
    return requests.post(SLACK_WEBHOOK, headers=headers, data=text_data)


@sched.scheduled_job('interval', minutes=10)
def timed_job():
    webpage = urllib.request.urlopen(req).read()
    page_soup = soup(webpage, "html.parser")
    for agent_loc in page_soup.find_all("location"):
        if agent_loc.id.text in regions:
            logging.info(agent_loc.id.text+" found. Checking testers.")
            if not check_active(agent_loc):
                logging.info("ALERT generated ...........")
                try:
                    mail_res = send_mail_alert(agent_loc.id.text, regions[agent_loc.id.text])
                    logging.info(mail_res)
                    logging.info(mail_res.content)
                    logging.info("alert sent to "+EMAIL_RECIPIENT)
                    slack_res = send_slack_alert(agent_loc.id.text, regions[agent_loc.id.text])
                    logging.info(slack_res)
                    logging.info(slack_res.content)
                    logging.info("alert sent to slack #actionkamen")
                except Exception as exp:
                    logging.info(str(exp))
                    logging.info(exp)

sched.start()