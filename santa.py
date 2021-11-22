from oauth2client.service_account import ServiceAccountCredentials
from secrets import secrets
import gspread
import random
import yagmail

# constants
NUM_PEOPLE = 6

# Google Sheets stuff
def get_data_from_google_sheets(sheets_url: str) -> "list[dict]":
    '''
        Returns data from Google Sheets as a list of dictionaries

        gspread tutorial: https://www.analyticsvidhya.com/blog/2020/07/read-and-update-google-spreadsheets-with-python/
    '''
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('secret-santa-service-account-key.json', scope)
    client = gspread.authorize(creds)
    google_sheet = client.open_by_url(sheets_url)
    sheet_data = google_sheet.worksheet("Data")
    list_of_dicts = sheet_data.get_all_records()
    return list_of_dicts

def create_people(sheets_data: "list[dict]") -> list:
    '''
        Returns a list of Person objects with data from sheets_data
    '''
    people = []
    for item in sheets_data:
        people.append(Person(item['Name'], item['Email'], item['SO'], item['Wishlist']))
    return people

def check_people_data(people: list) -> bool: 
    '''
        Checks that the list of Person objects has legitimate data
    '''
    for person in people: 
        if person.get_name() is None or len(person.get_name()) <= 0:
            return False
        if person.get_email() is None or len(person.get_email()) <= 0:
            return False
        if person.get_restriction() is None or len(person.get_restriction()) <= 0:
            return False
        if person.get_wishlist() is None or len(person.get_wishlist()) <= 0:
            return False
    return True

# Matching algorithm stuff 
class Person():
    '''
        A Person object contains the name, email, restriction, wishlist, and receiver of a participant 
    '''
    def __init__(self, name="", email="", restriction="", wishlist=""):
        self.name = name
        self.email = email
        self.restriction = restriction
        self.wishlist = wishlist
        self.receiver = None

    def get_name(self):
        return self.name

    def get_email(self):
        return self.email

    def get_restriction(self):
        return self.restriction
    
    def get_receiver(self):
        return self.receiver

    def set_receiver(self, receiver):
        self.receiver = receiver

    def get_wishlist(self):
        return self.wishlist

def match_name_to_person(people: list) -> dict: 
    '''
        Returns a dictionary mapping name (string) to person (object)
    '''
    name_to_person = {}
    for person in people: 
        name_to_person[person.get_name()] = person
    return name_to_person

def generate_starting_graph(names: list) -> dict:
    '''
        Returns a dictionary graph with edges from everyone to everyone (including self)
    '''    
    starting_graph = {}
    for name in names: 
        starting_graph[name] = names.copy()
    return starting_graph


def enforce_restrictions(graph: dict, name_to_person: dict) -> None: 
    '''
        Updates the graph by removing edges that fall under these restrictions:
            1. No one should be able to gift themselves.
            2. No one should be able to gift their significant other.

        Modifies the graph in place. 

        Doesn't return anything.
    '''
    for name in graph.keys():
        edges = graph[name]
        # remove self edge
        if name in edges:
            edges.remove(name)
        # remove SO edge 
        significant_other = get_person_from_name(name, name_to_person).get_restriction()
        if significant_other in edges:
            edges.remove(significant_other)

def set_matches(graph: dict, name_to_person: dict) -> None:
    '''
        Attempts to assign each person a receiver to gift to.

        Terminates early if the algorithm fails to give everyone a match that satisfies all constraints.
    '''
    # enforce restrictions, doesn't matter if this has been called before
    enforce_restrictions(graph, name_to_person) 

    for name in graph.keys():
        edges = graph[name]

        # if a person doesn't have anyone to gift to, terminate early
        if len(edges) == 0:
            print("Terminated early. Algorithm failed to find a proper solution.")
            return

        # select someone randomly
        receiver = random.choice(edges)

        # set the match
        gifter = get_person_from_name(name, name_to_person)
        gifter.set_receiver(receiver)

        # update the graph by removing the person who got matched from everyone else's edges 
        remove_receiver_from_edges(gifter.get_name(), receiver, graph)

def remove_receiver_from_edges(gifter: str, receiver: str, graph: dict) -> None:
    '''
        Updates the graph by removing the receiver from everyone but the gifter's edges
    '''
    for name in graph.keys():
        if name == gifter:
            continue
    
        edges = graph[name]
        if receiver in edges:
            edges.remove(receiver)


def get_person_from_name(name: str, name_to_person: dict) -> Person:
    '''
        Returns the Person object associated with a name
    '''
    return name_to_person[name]

def reset_matches(people: list):
    '''
        Resets all receivers to None.
    '''
    for person in people:
        person.receiver = None

def check_matches(people: list) -> bool:
    '''
        Returns true if all matches are satisfactory, false if not.
    '''
    for person in people:
        if person.get_receiver() == person.get_name() or person.get_receiver() == person.get_restriction() or person.get_receiver() == None:
            return False
    return True

def check_receivers(people: list, names: list) -> bool:
    '''
        Checks that everyone is a gift receiver.
    '''
    list_of_names = names.copy()
    for person in people:
        list_of_names.remove(person.get_receiver())
    
    if len(list_of_names) != 0:
        return False
    return True

def secret_santa(people: list, names: list, name_to_person: dict) -> dict:
    '''
        Returns a graph of secret santa pairings. 
    '''
    print("Generating matches...")
    count = 0
    while not check_matches(people):
        reset_matches(people)
        print(f'Matching Algorithm Attempt #{count}')
        graph = generate_starting_graph(names)
        enforce_restrictions(graph, name_to_person)
        set_matches(graph, name_to_person) 
        count += 1
    return graph

def print_matches(people: list) -> None:
    '''
        Prints gift-receiver pairings. Used for debugging purposes only.
    '''
    for person in people:
        print(f'{person.get_name()} is gifting to {person.get_receiver()}')

# Email stuff
def send_emails(people: list, name_to_person: list) -> None:
    """
        Sends out Secret Santa matchings via email
    """
    with yagmail.SMTP(secrets["email"], secrets["email_password"]) as yag:
        for person in people:
            print(f"Sending email to {person.get_name()}...")
            receiver_name = person.get_receiver()
            receiver = get_person_from_name(receiver_name, name_to_person)
            receiver_wishlist = receiver.get_wishlist()
            contents = [
                f'Ho ho ho! Happy holidays, {person.get_name()}!',
                f'I am Creekside Santa Bot and I am here today to give you a secret mission.',
                f'Your mission is to find {receiver_name} a gift for the holidays!',
                f'Here are some clues that might help you on your mission: {receiver_wishlist}',
                f'Best of luck!',
                f'Yours truly,',
                f'Creekside Santa Bot',
            ]
            subject = "Creekside Secret Santa 2021"
            try:
                yag.send(to=receiver.get_email(), subject=subject, contents=contents)
            except Exception as e:
                print(f'Exception occurred while sending email: {e}. Email address was: {receiver.get_email()}')
                return
            print("Email sent!")

def run_secret_santa():
    '''
        Fetches the information from the Google Sheet.
        Runs the matching algorithm. 
        Runs checks on the matches.
        Emails all the participants.
    '''
    print('Welcome to Secret Santa!')

    # getting information from google sheets
    print('Starting Google Sheets process...')
    sheets_data = get_data_from_google_sheets(secrets['gsheets_url'])
    people = create_people(sheets_data)

    # check people data
    if len(people) != NUM_PEOPLE:
        print("The number of Person objects in the people list is incorrect. Please double check the Google Sheets.")
        return
    if not check_people_data(people):
        print("People data have not been populated correctly. Check failed.")
        return

    name_to_person = match_name_to_person(people)
    names = list(name_to_person.keys())
    print('Google Sheets process complete!')

    # matching algorithm 
    print('Starting matching process...')
    graph_of_matches = secret_santa(people, names, name_to_person)
    print("Matching process complete!")

    # check matches 
    print("Starting checking process...")
    if not check_matches(people):
        print("Algorithm failed to set proper matches. Please run the program again.")
        return
    if not check_receivers(people, names):
        print("Not everyone was set as a receiver properly.")
        return
    print("Checking process complete!")

    # uncomment if debugging only
    # print_matches(people)

    # email people 
    print('Starting email process...')
    send_emails(people, name_to_person)
    print("Email process complete!")

    print("All steps have completed. Have a nice day!")

if __name__ == '__main__':
    run_secret_santa()

