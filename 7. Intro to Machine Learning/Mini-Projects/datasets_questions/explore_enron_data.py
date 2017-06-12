#!/usr/bin/python

"""
    Starter code for exploring the Enron dataset (emails + finances);
    loads up the dataset (pickled dict of dicts).

    The dataset has the form:
    enron_data["LASTNAME FIRSTNAME MIDDLEINITIAL"] = { features_dict }

    {features_dict} is a dictionary of features associated with that person.
    You should explore features_dict as part of the mini-project,
    but here's an example to get you started:

    enron_data["SKILLING JEFFREY K"]["bonus"] = 5600000

"""

import pickle

enron_data = pickle.load(open("../final_project/final_project_dataset.pkl", "r"))
print("Number of people: {}".format(len(enron_data)))
print("Number of features: {}".format(len(enron_data["METTS MARK"])))

# Access data with enron_data["LASTNAME FIRSTNAME MIDDLEINITIAL"]["feature_name"]

print("Total value of the stock of James Prentice: {}".format(enron_data["PRENTICE JAMES"]["total_stock_value"]))
print("Number of emails from Wesley Colwell: {}".format(enron_data["COLWELL WESLEY"]["from_this_person_to_poi"]))
print("Number of stock options exercised by Jeffrey K Skilling: {}".format(enron_data["SKILLING JEFFREY K"]["exercised_stock_options"]))
