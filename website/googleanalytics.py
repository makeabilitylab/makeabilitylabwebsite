"""A simple example of how to access the Google Analytics API."""

import argparse

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools
import os

from . import googleaccount



def get_service(api_name, api_version, scope, key_file_location,
                service_account_email):
  """Get a service that communicates to a Google API.

  Args:
    api_name: The name of the api to connect to.
    api_version: The api version to connect to.
    scope: A list auth scopes to authorize for the application.
    key_file_location: The path to a valid service account p12 key file.
    service_account_email: The service account email address.

  Returns:
    A service that is connected to the specified API.
  """

  credentials = ServiceAccountCredentials.from_p12_keyfile(
    service_account_email, key_file_location, scopes=scope)

  http = credentials.authorize(httplib2.Http())

  # Build the service object.
  service = build(api_name, api_version, http=http)

  return service


def get_first_profile_id(service):
  # Use the Analytics service object to get the first profile id.

  # Get a list of all Google Analytics accounts for this user
  accounts = service.management().accounts().list().execute()

  if accounts.get('items'):
    # Get the first Google Analytics account.
    account = accounts.get('items')[0].get('id')

    # Get a list of all the properties for the first account.
    properties = service.management().webproperties().list(
        accountId=account).execute()

    if properties.get('items'):
      # Get the first property id.
      property = properties.get('items')[0].get('id')

      # Get a list of all views (profiles) for the first property.
      profiles = service.management().profiles().list(
          accountId=account,
          webPropertyId=property).execute()

      if profiles.get('items'):
        # return the first view (profile) id.
        return profiles.get('items')[0].get('id')

  return None


#This is a sample from the original with some modifications which has been left here as an example
def get_results(service, profile_id):
  # Use the Analytics Service Object to query the Core Reporting API
  # for the number of sessions within the past seven days.
  return service.data().ga().get(
    ids='ga:' + profile_id,
    start_date='30daysAgo',
    end_date='today',
    metrics='ga:pageviews',
    dimensions='ga:PagePathLevel1,ga:PagePathLevel2'
  ).execute()



#Accepts a function to call against the api after setting up the required variables. This is essentially just a module to run any function with the analytics api.
def run(request_func):
  # Define the auth scopes to request.
  scope = ['https://www.googleapis.com/auth/analytics.readonly']

  # Use the developer console and replace the values with your
  # service account email and relative location of your key file.
  # service account in git ignored file
  service_account_email = googleaccount.ANALYTICS_ACCOUNT
  file_path=os.path.dirname(os.path.abspath(__file__))
  key_file_location = file_path+'/googlekey.p12'

  # Authenticate and construct service.
  service = get_service('analytics', 'v3', scope, key_file_location,
    service_account_email)
  profile = get_first_profile_id(service)
  return request_func(service, profile)


