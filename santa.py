import random


import yagmail

from secrets import secrets

"""
graph = {'A': ['B', 'C'],
        'B': ['C', 'D'],
        'C': ['D'],
        'D': ['C'],
        'E': ['F'],
        'F': ['C']}
"""

class Person():
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


def hardcode_names() -> list: 
    return ["An", "Virginia", "Tom", "Jessica", "Elle", "Vincent"]

def hardcode_people() -> list: 
    return [
      Person("An", "test", "Virginia", "test"),
        Person("Virginia", "test", "An", "test"),
        Person("Tom", "test", "Jessica", "test"),
        Person("Jessica", "test", "Tom", "test"),
        Person("Elle", "test", "Vincent", "test"),
        Person("Vincent", "test", "Elle", "test"),
    ]

def create_people() -> list:
    listy = []
    for i in range(100):
        listy.append(Person(str(i), "test", f'{i}_prime'))
        listy.append(Person(f'{i}_prime', "test", str(i)))
    return listy

def create_names() -> list:
    listy = []
    for i in range(100):
        listy.append(str(i))
        listy.append(f'{i}_prime')
    return listy

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
    # enforce restrictions 
    # doesn't matter if this has been called before
    enforce_restrictions(graph, name_to_person) 

    for name in graph.keys():
        print(graph)
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

def secret_santa(people: list, names: list, name_to_person: dict) -> dict:
    '''
        Returns a graph of secret santa pairings. 
    '''
    print("Generating matches...")
    count = 0
    while not check_matches(people):
        reset_matches(people)
        print(f'Attempt #{count}')
        graph = generate_starting_graph(names)
        enforce_restrictions(graph, name_to_person)
        set_matches(graph, name_to_person) 
        count += 1
    return graph

def print_matches(people: list) -> None:
    '''
        Prints gift-receiver pairings.
    '''
    for person in people:
        print(f'{person.get_name()} is gifting to {person.get_receiver()}')

def attempt():
    names = hardcode_names() 
    people = hardcode_people()
    name_to_person = match_name_to_person(people)
    graph_of_matches = secret_santa(people, names, name_to_person)
    # do some checking here lol, assertions 
    # checking can happen in either graph or in in person's objects
    print_matches(people)

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
            yag.send(to=receiver.get_email(), subject=subject, contents=contents)
            print("Email sent!")
