#!/usr/bin/python3.6
"""Runs bots for a Discord server."""
import re
import math
import subprocess
import argparse
import random
import time
import datetime
import csv
import json
from html.parser import HTMLParser
import requests
import discord
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ABSPATH = "/home/austin/Documents/mathbot"
STREAK_INCREASE = 11.58
ENGINE = create_engine(f"sqlite:///{ABSPATH}/dbs/clan_info.db")
MASTER_SESSION = sessionmaker(bind=ENGINE)
BASE = declarative_base()
REQUEST_SESSION = requests.session()
SESSION = MASTER_SESSION()

class Account(BASE):
    """Defines the class to handle account names and historical caps"""
    __tablename__ = 'account'
    name = Column(String(50), primary_key=True)
    last_cap_time = Column(DateTime)
    total_caps = Column(Integer)

class CheckInfo(BASE):
    """Stores if a user satisfies a check or not"""
    __tablename__ = 'checkInfo'
    name = Column(String(50), primary_key=True)
    satisfies = Column(Boolean)

def init_db():
    """Initializes and optionally clears out the database"""
    BASE.metadata.bind = ENGINE
    BASE.metadata.create_all(ENGINE)

def upsert(table, primary_key_map, obj):
    """Decides whether to insert or update an object."""
    first = SESSION.query(table).filter_by(**primary_key_map).first()
    if first != None:
        keys = table.__table__.columns.keys()
        SESSION.query(table).filter_by(**primary_key_map).update(
            {column: getattr(obj, column) for column in keys})
        return None
    return obj

class MyHTMLParser(HTMLParser):
    """Builds an HTML parser."""
    def handle_data(self, data):
        if data.startswith("\nvar data;"):
            list_start = data.find("[")
            list_end = data.find("]")
            clan_members = data[list_start+1:list_end]
            clan_members = clan_members.split(", ")
            clan_list = []
            for item in clan_members:
                add_item = item[1:-1]
                add_item = add_item.replace(u'\xa0', u' ')
                clan_list.append(add_item)
            self.data = clan_list

def main():
    """Runs the stuff."""
    parser = argparse.ArgumentParser(description="Choose script actions.")
    parser.add_argument(
        "-a", "--all", help="Runs user checks, cap check, and bot.", action="store_true")
    parser.add_argument("-c", "--check", help="Runs the cap check.", action="store_true")
    parser.add_argument("-u", "--update", help="Runs only user checks.", action="store_true")
    parser.add_argument("-b", "--bot", help="Runs only the bot.", action="store_true")
    parser.add_argument("-i", "--init", help="Reinitializes the databases.", action="store_true")
    args = parser.parse_args()
    token = ""
    with open(f"{ABSPATH}/tokens/token.txt", "r") as token_file:
        token = token_file.read().strip()
    if args.all or args.check or args.update:
        capped_users = []
        if not args.update:
            clan_parser = MyHTMLParser()
            url_str = ""
            with open(f"{ABSPATH}/tokens/clan_url.txt", "r") as url_file:
                url_str = url_file.read().strip()
            req_data = requests.get(url_str)
            req_html = req_data.text
            clan_parser.feed(req_html)
            clan_list = clan_parser.data
            capped_users = add_cap_to_db(clan_list)
        if not args.check:
            with open(f"{ABSPATH}/checks/checkfile.csv", "r") as check_file:
                reader = csv.DictReader(check_file)
                for check in reader:
                    add_check_to_db(check['name'], check['string'])
        if args.all:
            run_bot(capped_users, token)
    elif args.init:
        init_db()
    elif args.bot:
        run_bot([], token)

def run_bot(capped_users, token):
    """Actually runs the bot"""
    # The regular bot definition things
    client = discord.Client()

    @client.event
    async def on_ready():
        """Prints bot initialization info"""
        print('Logged in as')
        print(client.user.name)
        print(client.user.id)
        print('------')

    @client.event
    async def on_message(message):
        """Handles commands based on messages sent"""

        channel = message.channel
        channel_id = message.channel.id
        content = message.content
        author = message.author
        author_name = author.name
        role_list = [role.name for role in author.roles]
        command_map = {"$telos": telos_command,
                       "$pet": pet_command}
        reaction_pct = random.random()

        cap_channel = ""
        with open(f"{ABSPATH}/tokens/channel.txt", "r+") as channel_file:
            cap_channel = channel_file.read().strip()

        with open(f"{ABSPATH}/textfiles/victim.txt", "r+") as victim_file:
            victim = victim_file.read().strip().split("~")[0]
            if victim == author_name and reaction_pct < 1:
                emojis = list(client.get_all_emojis())
                add_emoji = random.sample(emojis, 1)[0]
                # for emoji in emojis:
                #     if emoji.name == "nice":
                #         nice_emoji = emoji
                await client.add_reaction(message, add_emoji)

        for command, func in command_map.items():
            if content.startswith(command):
                out_msg = func(content)
                if out_msg is not None:
                    await client.send_message(channel, out_msg)


        # schep_questions = ["does schep have tess", "did schep get tess", "does schep have tess yet"]
        # milow_questions = ["does milow have ace", "did milow get ace", "does milow have ace yet"]
        # if (content.lower() in schep_questions) or (content.lower()[:-1] in schep_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Schep").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await client.send_message(channel, f"Schep does not have Tess, make sure to let him know ;)", tts=True)
        #     else:
        #         await client.send_message(channel, f"Schep finally got Tess!")

        # elif (content.lower() in milow_questions) or (content.lower()[:-1] in milow_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Milow").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await client.send_message(channel, f"Milow does not have Ace.", tts=True)
        #     else:
        #         await client.send_message(channel, f"Milow finally got Ace!")

        if content.startswith("$help"):
            out_msg = "Try '$telos help' or '$pet help'."
            await client.send_message(channel, out_msg)

        elif content.startswith("$bosslist"):
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            bosses = list(droprate_json.keys())
            await client.send_message(channel, f"The tracked bosses are: {bosses}")

        elif content.startswith("$droplist"):
            query_list = content.split(" ")
            boss = query_list[1].lower()
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            try:
                droplist = droprate_json[boss]
                drops = list(droplist.keys())
                await client.send_message(channel, f"The drops for {boss} are: {drops}")
            except KeyError:
                await client.send_message(channel, "The requested boss isn't listed.")

        elif content.startswith("$drop"):
            query_list = content.split(" ")
            boss = query_list[1].lower()
            item = " ".join(query_list[2:]).lower()
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            try:
                droprate = droprate_json[boss][item]
                await client.send_message(
                    channel, f"The droprate for {boss} of {item} is: 1/{droprate}")
            except KeyError:
                await client.send_message(channel, "Specified drop or boss not listed.")

        elif content.startswith('!reboot') and "cap handler" in role_list:
            await client.send_message(channel, "Rebooting bot.")
            subprocess.call(['./runmathbot.sh'])

        elif content.lower().startswith("<@!410521956954275850> when will"):
            await client.send_message(channel, f":crystal_ball: Soon:tm: :crystal_ball:")

        elif content.lower().startswith("markdonalds"):
            emojis = client.get_all_emojis()
            for emoji in emojis:
                if emoji.name == "mRage":
                    luke_emoji = emoji
            await client.send_message(channel, f"{luke_emoji}")

        elif content.startswith("!add") and author_name == "Roscroft":
            new_row = content[5:]
            new_row += "\n"
            with open(f"{ABSPATH}/textfiles/responses.csv", "a+") as responses:
                responses.write(new_row)

        elif content.startswith("!player") and author_name == "Roscroft":
            victim = content[8:]
            now = datetime.datetime.now()
            with open(f"{ABSPATH}/textfiles/victim.txt", "w+") as victim_file:
                victim_file.write(f"{victim}~{now}")

        elif content.startswith("!pairings") and author_name == "Roscroft":
            server = client.get_server("339514092106678273")
            members = list(server.members)
            await client.send_message(
                channel, f"This would result in {len(members)*len(members)} messages.")
            # for member1 in members:
            #     for member2 in members:
            #         await client.send_message(channel, f"--ship {member1} {member2}")

        elif content.startswith('!vis'):
            await client.send_message(channel, "It's actually ~vis")

        elif channel_id == cap_channel:
            if content.startswith('!delmsgs') and ("cap handler" in role_list):
                info = content.split(" ")[1]
                if info == "all":
                    async for msg in client.logs_from(channel, limit=1000):
                        if msg.author == client.user:
                            time.sleep(1)
                            await client.delete_message(msg)
                elif info == "noncap":
                    async for msg in client.logs_from(channel, limit=1000):
                        if msg.author == client.user and "capped" not in msg.content:
                            time.sleep(1)
                            await client.delete_message(msg)
                else:
                    # Try to interpret info as a message id. Thankfully bots fail gracefully
                    before_msg = await client.get_message(channel, info)
                    async for msg in client.logs_from(channel, limit=1000, before=before_msg):
                        if msg.author == client.user:
                            time.sleep(1)
                            await client.delete_message(msg)

            elif content.startswith('!help'):
                await client.send_message(
                    channel, ("Commands:\n!delmsgs <argument> - using a message id will "
                              "delete all messages before that id. Using 'all' will delete "
                              "all messages, and using 'noncap' will delete all non-cap report "
                              "messages.\n!update - force a manual check of all alogs.\n!list "
                              "- generates a list of all users who have capped recently, by "
                              "looking at cap reports in the channel. Note that if there are "
                              "no cap messages, this will do nothing.\n!force <argument> - "
                              "the bot will check the database for cap info about the user, "
                              "and will send a message to the channel if cap info exists. "
                              "Using 'all' will send an update message to the channel for "
                              "every user in the database."))

            elif content.startswith('!list'):
                userlist = []
                async for msg in client.logs_from(channel, limit=500):
                    if msg.author == client.user and ("capped" in msg.content):
                        msg_lines = msg.content.split("\n")
                        for cap_report in msg_lines:
                            name_index = cap_report.find(" has")
                            userlist.append(cap_report[:name_index])
                print(userlist)
                ret_str = ""
                for i in range(len(userlist)):
                    ret_str += f"{i+1}. {userlist[i]}\n"
                await client.send_message(channel, ret_str)

            elif content.startswith('!update') and ("cap handler" in role_list):
                await client.send_message(channel, "Manually updating...")
                subprocess.call(['./runmathbot.sh'])

            elif content.startswith('!force') and ("cap handler" in role_list):
                user = content.split(" ")[1]
                if user == "all":
                    capped_users = SESSION.query(Account.name, Account.last_cap_time).all()
                    for (user, cap_date) in capped_users:
                        cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                        datetime_list = cap_date.split(" ")
                        date_report = datetime_list[0]
                        time_report = datetime_list[1]
                        msg_string = (f"{user} has capped at the citadel on {date_report} ",
                                      f"at {time_report}.")
                        await client.send_message(
                            discord.Object(id=cap_channel), msg_string)
                else:
                    cap_date = SESSION.query(
                        Account.last_cap_time).filter(Account.name == user).first()
                    if cap_date is not None:
                        cap_date = cap_date[0]
                        with open(f"{ABSPATH}/tokens/channel.txt", "r") as channel_file:
                            cap_channel = channel_file.read().strip()
                        cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                        datetime_list = cap_date.split(" ")
                        date_report = datetime_list[0]
                        time_report = datetime_list[1]
                        msg_string = (f"{user} has capped at the citadel on {date_report} ",
                                      "at {time_report}.")
                        await client.send_message(discord.Object(id=cap_channel), msg_string)

        else:
            with open(f"{ABSPATH}/textfiles/responses.csv", "r+") as responses:
                reader = csv.DictReader(responses)
                for response in reader:
                    if response['call'] in content.lower():
                        await client.send_message(channel, f"{response['answer']}")

    async def choose_victim():
        """Chooses a victim to add reactions to"""
        await client.wait_until_ready()
        now = datetime.datetime.now()
        with open(f"{ABSPATH}/textfiles/victim.txt", "r+") as victim_file:
            victim_list = victim_file.read().strip().split("~")
            victim = victim_list[0]
            try:
                timestamp = datetime.datetime.strptime(victim_list[1], "%Y-%m-%d %H:%M:%S.%f")
                hours_since = (now-timestamp).seconds//3600
            except IndexError:
                timestamp = None
                hours_since = None
            if timestamp is None or victim == "" or hours_since < 6:
                server = client.get_server("339514092106678273")
                members = list(server.members)
                victim = random.sample(members, 1)[0]
                print(f"New victim: {victim.name}")
                victim_file.seek(0)
                victim_file.truncate()
                victim_file.write(f"{victim.name}~{now}")

    async def report_caps(capped_users):
        """Reports caps."""
        await client.wait_until_ready()
        with open(f"{ABSPATH}/tokens/channel.txt", "r") as channel_file:
            cap_channel = channel_file.read().strip()
        capped_users.reverse()
        for (user, cap_date) in capped_users:
            datetime_list = cap_date.split(" ")
            date_report = datetime_list[0]
            time_report = datetime_list[1]
            msg_string = f"{user} has capped at the citadel on {date_report} at {time_report}."
            await client.send_message(discord.Object(id=cap_channel), msg_string)

    client.loop.create_task(choose_victim())
    client.loop.create_task(report_caps(capped_users))
    client.run(token)

def check_alog(username, search_string):
    """Returns date if search string is in user history, or if it has previously been recorded."""
    url_str = ""
    with open(f"{ABSPATH}/tokens/url.txt", "r") as url_file:
        url_str = url_file.read().strip()
    url_str += username
    url_str += "&activities=20"
    data = REQUEST_SESSION.get(url_str).content
    data_json = json.loads(data)
    try:
        activities = data_json['activities']
    except KeyError:
        print(f"{username}'s profile is private.")
        return None
    for activity in activities:
        if search_string in activity['details']:
            date = activity['date']
            print(f"{search_string} found: {username}, {date}")
            return activity['date']
    return None

def add_cap_to_db(clan_list):
    """Displays cap info for a list of users."""
    add_list = []
    capped_users = []
    for user in clan_list:
        cap_date = check_alog(user, "capped")
        if cap_date is not None:
            db_date = datetime.datetime.strptime(cap_date, "%d-%b-%Y %H:%M")
            # cap_date = datetime.datetime.strptime(cap_date, "%a, %d %b %Y %H:%M:%S %Z")
            # If the cap date is not None, that means the user has a cap in their adventurer's log.
            # We need to do a few things. First, check to see if the cap date is already stored in
            # the database under last_cap_reported
            previous_report = SESSION.query(
                Account.last_cap_time).filter(Account.name == user).first()
            # Two outcomes: previous report is None, or it has a value. If it is none, then we
            # update it to be cap_date, and store the current time as last_cap_actual.
            # If it has a value, and it is the same as cap_date, we don't do anything. If it
            # has a different value, then we need to update the account dict in the same way as
            # if the previous report is none.
            if previous_report is None or previous_report[0] < db_date:
                # Check to see if the time is in the database. If so, probably indicates a name
                # change. If the time is already in, then we do not need to report it.
                same_time = SESSION.query(
                    Account.name, Account.last_cap_time).filter(
                        Account.last_cap_time == db_date).first()
                if same_time is not None:
                    print("Name change found.")
                else:
                    primary_key_map = {"name": user}
                    account_dict = {"name": user, "last_cap_time": db_date}
                    account_record = Account(**account_dict)
                    add_list.append(upsert(Account, primary_key_map, account_record))
                    print(f"{user} last capped at the citadel on {cap_date}.")
                    capped_users.append((user, cap_date))
                    # print(capped_users)
        else:
            pass
            # print(f"{user} has not capped at the citadel.")

    add_list = [item for item in add_list if item is not None]
    SESSION.add_all(add_list)
    SESSION.commit()
    return capped_users


def add_check_to_db(username, search_string):
    """Updates a user's record with results of the check."""
    add_list = []
    check_res = check_alog(username, search_string)
    if check_res is not None:
        check_report = SESSION.query(CheckInfo.satisfies).filter(CheckInfo.name == username).first()
        if check_report is None or check_report[0] is False:
            primary_key_map = {"name": username}
            account_dict = {"name": username, "satisfies": check_res}
            account_record = CheckInfo(**account_dict)
            add_list.append(upsert(CheckInfo, primary_key_map, account_record))
    add_list = [item for item in add_list if item is not None]
    SESSION.add_all(add_list)
    SESSION.commit()

def pet_chance(droprate, threshold, killcount):
    """Calls recursive pet_chance_counter function to determine chance of not getting pet."""
    def pet_chance_counter(droprate, threshold, killcount, threshold_counter):
        """Calculates chance of not getting pet recursively."""
        if killcount < threshold or threshold_counter == 9:
            return math.pow((1-(threshold_counter/droprate)), killcount)
        chance = math.pow((1-(threshold_counter/droprate)), threshold)
        killcount = killcount - threshold
        threshold_counter += 1
        return chance*pet_chance_counter(droprate, threshold, killcount, threshold_counter)
    chance = pet_chance_counter(droprate, threshold, killcount, 1)
    chance *= 100
    return truncate_decimals(chance)

def telos(enrage, streak, lotd):
    """Returns the drop chance at a given enrage and streak, with or without LotD."""
    denominator = math.floor(10000.0/(10+0.25*(enrage+25*lotd)+3*streak))
    cap = 9
    if denominator < cap:
        return 1.0/cap
    return 1/denominator

def expected_uniques(start_enrage, end_enrage):
    """Given a start enrage and end enrage, returns expected number of uniques and kills."""
    streak_total = math.ceil((end_enrage-start_enrage)/STREAK_INCREASE)
    sum_of_expectations_lotd = 0.0
    sum_of_expectations_no_lotd = 0.0
    for i in range(1, streak_total + 1):
        enrage = start_enrage + STREAK_INCREASE*i
        streak = i
        sum_of_expectations_lotd += telos(enrage, streak, 1)
        sum_of_expectations_no_lotd += telos(enrage, streak, 0)
    sum_of_expectations_no_lotd = truncate_decimals(sum_of_expectations_no_lotd)
    sum_of_expectations_lotd = truncate_decimals(sum_of_expectations_lotd)
    return (sum_of_expectations_no_lotd, sum_of_expectations_lotd, streak_total)

def kills_until_unique(start_enrage):
    """Given a start enrage, return the expected number of kills until a unique is obtained."""
    expected_uniques_lotd = 0.0
    expected_uniques_no_lotd = 0.0
    streak = 0
    while expected_uniques_lotd <= 1:
        enrage = start_enrage + STREAK_INCREASE*streak
        expected_uniques_lotd += telos(enrage, streak, 1)
        streak += 1
    kills_for_lotd_unique = streak
    streak = 0
    while expected_uniques_no_lotd <= 1:
        enrage = start_enrage + STREAK_INCREASE*streak
        expected_uniques_lotd += telos(enrage, streak, 1)
        expected_uniques_no_lotd += telos(enrage, streak, 0)
        streak += 1
    kills_for_no_lotd_unique = streak
    return (kills_for_no_lotd_unique, kills_for_lotd_unique)

def truncate_decimals(num):
    """Replaced my old function with a builtin, can decide on significance."""
    return "{0:.4g}".format(num)

def telos_command(content):
    """Processes telos commands and answers queries for correctly formatted requests."""
    try:
        def bounds_reply(match):
            """Returns data on enrage bounds queries."""
            start_enrage = int(match.group(1))
            end_enrage = int(match.group(2))
            if start_enrage > end_enrage:
                raise ValueError("Start enrage must be less than end enrage.")
            (no_lotd, lotd, streak_total) = expected_uniques(start_enrage, end_enrage)
            out_msg = (f"Streaking from {start_enrage}% to {end_enrage}%:\n"
                       f"Expected number of kills: {streak_total}\n"
                       f"Expected uniques: {no_lotd} without LotD, {lotd} with LotD.")
            return out_msg

        def start_reply(match):
            """Returns data on start enrage queries."""
            out_msg = ""
            start_enrage = int(match.group(1))
            if start_enrage > 4000:
                out_msg = "Using an enrage of 4000 (max chance).\n"
                start_enrage = 4000
            (no_lotd, lotd) = kills_until_unique(start_enrage)
            out_msg += (f"Streaking from {start_enrage}%:\n"
                        f"Expected kills until unique: {no_lotd} without LotD, "
                        f"{lotd} with LotD.")
            return out_msg

        def chance_reply(match):
            """Returns data on individual chance queries."""
            out_msg = ""
            enrage = int(match.group(1))
            streak = int(match.group(2))
            if enrage > 4000:
                out_msg = "Using an enrage of 4000 (max chance).\n"
                enrage = 4000
            no_lotd = telos(enrage, streak, 0)
            lotd = telos(enrage, streak, 1)
            print(no_lotd)
            print(lotd)
            out_msg += (f"A kill with enrage {enrage}% and streak {streak}:\n"
                        f"Unique chance: 1/{int(1/no_lotd)} without LotD, "
                        f"1/{int(1/lotd)} with LotD.")
            return out_msg

        def pet_reply(match):
            """Returns data on pet queries."""
            killcount = int(match.group(1))
            droprate = 700
            threshold = 300
            pet = pet_chance(droprate, threshold, killcount)
            out_msg = f"Your chance of not getting Tess by now is: {pet}%"
            return out_msg

        def help_reply(match):
            """Returns help information."""
            del match
            out_msg = ("List of commands:\n$telos <enrage>% <enrage>% - returns expected "
                       "uniques when streaking from the first enrage to the second enrage."
                       "\n$telos <enrage>% - returns expected number of kills until a "
                       "unique is obtained when starting at the given enrage.\n"
                       "$telos <enrage>% <streak>kc - returns the chance of obtaining a "
                       "unique with a kill at the given enrage and streak.\n"
                       "$telos pet <killcount> - returns the chance of not getting the pet "
                       "by the time you have hit the given killcount.\n"
                       "$telos help - returns the above list.")
            return out_msg

        regex_handlers = {}
        regex_handlers[r"\$telos (\d{1,4})% (\d+)%"] = bounds_reply
        regex_handlers[r"\$telos (\d{1,4})%"] = start_reply
        regex_handlers[r"\$telos (\d{1,4})% (\d+)kc"] = chance_reply
        regex_handlers[r"\$telos pet (\d+)"] = pet_reply
        regex_handlers[r"\$telos help"] = help_reply

        out_msg = None

        for regex, func in regex_handlers.items():
            match = re.compile(regex).fullmatch(content)
            if match:
                out_msg = func(match)

        return out_msg

    except ValueError as inst:
        return f"{inst}"

def pet_command(content):
    """Processes pet commands and returns chance or droprate information."""
    content = content.lower()
    try:
        droprates = json.load(open(f"{ABSPATH}/droprates.json"))
        boss_list = droprates.keys()
        boss_str = "(" + "|".join(boss_list) + ")"

        def droprate_reply(match):
            """Returns pet droprate info for normal mode and hard mode."""
            boss = match.group(1)
            boss_entry = droprates[boss]
            pet_info = boss_entry.get("pet")
            if pet_info is None:
                raise ValueError(f"No pet information listed for {boss}.")
            pet_hm_info = boss_entry.get("pet (hm)")
            if boss == "telos":
                out_msg = (f"With <100% enrage, Tess has droprate 1/{pet_info[0]} and threshold "
                           f"{pet_info[1]}. With >100% enrage, Tess has droprate "
                           f"1/{pet_hm_info[0]} and threshold {pet_hm_info[1]}.")
            else:
                out_msg = (f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold "
                           f"{pet_info[1]}.")
                if pet_hm_info is not None:
                    out_msg += (f"The pet from hardmode {boss} has droprate 1/{pet_hm_info[0]} and "
                                f"threshold {pet_hm_info[1]}.")
            return out_msg

        def chance_helper(match, hardmode):
            """Returns pet chance with the given killcount."""
            boss = match.group(1)
            boss_entry = droprates[boss]
            pet_info = boss_entry.get("pet")
            if pet_info is None:
                raise ValueError(f"No pet information listed for {boss}.")
            pet_hm_info = boss_entry.get("pet (hm)")
            killcount = int(match.group(2))
            if boss == "telos":
                chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
                out_msg = f"Your chance of not getting Tess by now is: {chance}%"
            else:
                if hardmode:
                    if pet_hm_info is None:
                        out_msg = "No difference in pet chance, using normal mode.\n"
                        out_msg += chance_helper(match, 0)
                    else:
                        chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
                        out_msg = (f"Your chance of not getting the pet by now in hardmode "
                                   f"is: {chance}%")
                else:
                    chance = pet_chance(pet_info[0], pet_info[1], killcount)
                    out_msg = f"Your chance of not getting the pet by now is: {chance}%"
            return out_msg

        def chance_reply(match):
            """Calls chance_helper and specifies normal mode."""
            return chance_helper(match, 0)

        def hm_chance_reply(match):
            """Calls chance_helper and specifies hard mode."""
            return chance_helper(match, 1)

        def manual_reply(match):
            """Manually calculates pet chance with given threshold and droprate."""
            droprate = int(match.group(1))
            threshold = int(match.group(2))
            killcount = int(match.group(3))
            if droprate < 1:
                raise ValueError("Invalid droprate (use the denominator).")
            elif threshold < 0:
                raise ValueError("Invalid threshold.")
            elif killcount < 0:
                raise ValueError("Invalid killcount")
            else:
                chance = pet_chance(droprate, threshold, killcount)
                out_msg = f"Your chance of not getting the pet by now is: {chance}%"
            return out_msg

        def help_reply(match):
            """Returns a help message for pets."""
            del match
            out_msg = ("List of commands:\n$pet <boss_str> - displays pet droprate for boss."
                       "\n$pet <boss_str> <killcount> - displays chance of getting boss pet with "
                       "given killcount."
                       "\n$pet hm <boss_str> <killcount> - displays chance of getting boss pet in"
                       " hardmode with given killcount."
                       "\n$pet <droprate> <threshold> <killcount> - displays chance of getting "
                       "boss pet, with given droprate, threshold, and killcount."
                       "$pet help - returns the above list.")
            return out_msg


        regex_handlers = {}
        regex_handlers[r"\$pet " + f"{boss_str}"] = droprate_reply
        regex_handlers[r"\$pet " + f"{boss_str}" + r" (\d+)"] = chance_reply
        regex_handlers[r"\$pet hm " + f"{boss_str}" + r" (\d+)"] = hm_chance_reply
        regex_handlers[r"\$pet (\d+) (\d+) (\d+)"] = manual_reply
        regex_handlers[r"\$pet help"] = help_reply

        out_msg = None

        for regex, func in regex_handlers.items():
            match = re.compile(regex).fullmatch(content)
            if match:
                out_msg = func(match)

        return out_msg

    except ValueError as inst:
        return f"{inst}"

if __name__ == "__main__":
    main()
