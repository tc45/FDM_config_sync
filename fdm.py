import requests
import time
import datetime


class FDMClient:

    def __init__(self, host, port=443, username='admin', password='1234QWer', log=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.log = log
        if not log:
            raise Exception('The logger should not be None.')

        self.token = None
        self.base_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        self.base_url = f'https://{self.host}:{self.port}/api/fdm/v5'

        requests.packages.urllib3.disable_warnings()

        self.log.debug('FDMClient class initialization finished.')

    def _send_request(self, url, method='get', headers=None, body=None, params=None):
        self.log.debug('Sending request to FDM')
        request_method = getattr(requests, method)
        if not headers:
            headers = self.base_headers

        self.log.debug(f'Using URL: {url}')
        self.log.debug(f'Using method: {method}')
        self.log.debug(f'Using headers: {str(headers)}')
        self.log.debug(f'Using body: {str(body)}')
        self.log.debug(f'Using query strings: {str(params)}')

        response = request_method(url, verify=False, headers=headers, json=body, params=params)
        status_code = response.status_code
        response_body = response.json()
        self.log.debug(f'Got status code: {str(status_code)}')
        self.log.debug(f'Got response body: {str(response_body)}')
        if status_code != 200:
            msg = response_body.get('message', 'Request to FDM unsuccessful.')
        return response_body

    def login(self):
        self.log.debug('Login to FDM.')

        url = self.base_url + '/fdm/token'

        body = {
            'grant_type': 'password',
            'username': f'{self.username}',
            'password': f'{self.password}',
        }

        self.log.debug('Sending the login request to FDM.')
        response = self._send_request(url, method='post', body=body)
        self.token = response.get('access_token')
        self.log.debug(f'Access token: {self.token}')

    def logout(self):
        self.log.debug('Logout from FDM.')
        url = self.base_url + '/fdm/token'
        body = {
            'grant_type': 'revoke_token',
            'access_token': self.token,
            'token_to_revoke': self.token,
        }

        self.log.debug('Sending the logout request to FDM.')
        self._send_request(url, method='post', body=body)
        self.log.debug('Logout successful.')

    def _get_auth_headers(self):
        headers = self.base_headers.copy()
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        else:
            msg = 'No token exists, use login method to get the token.'
            raise Exception(msg)
        return headers

    def get_access_policy_id(self):
        url = self.base_url + '/policy/accesspolicies'
        headers = self._get_auth_headers()

        self.log.debug('Requesting access policies from FDM.')
        response = self._send_request(url, headers=headers)
        policy_id = response['items'][0]['id']
        self.log.debug(f'Policy ID is: {policy_id}')
        return policy_id

    def create_access_rule(self, name):
        self.log.info(f'Creating access rule "{name}".')

    def get_access_rule_by_name(self, name):
        self.log.debug('Searching for access rule.')
        policy_id = self.get_access_policy_id()

        url = self.base_url + f'/policy/accesspolicies/{policy_id}/accessrules'
        headers = self._get_auth_headers()

        self.log.debug('Requesting access rules from FDM.')
        response = self._send_request(url, headers=headers)
        access_rules = response.get('items')

        rule_data = None
        for rule in access_rules:
            if name == rule.get('name'):
                rule_data = rule
                break
        if rule_data is None:
            self.create_access_rule(name)
            raise Exception('Unable to find requested rule.')
        return rule_data

    def get_url_categories(self):
        self.log.debug('Searching for URL categories on FDM.')
        url = self.base_url + '/object/urlcategories'
        headers = self._get_auth_headers()
        params = {'limit': '100'}

        self.log.debug('Sending request for getting URL categories from FDM.')
        response = self._send_request(url, headers=headers, params=params)
        return response.get('items')

    def put_access_rule(self, data):
        self.log.debug('Updating access rule on FDM.')
        url = data['links']['self']
        headers = self._get_auth_headers()

        self.log.debug('Sending the request to update the access rule on FDM.')
        response = self._send_request(url, method='put', headers=headers, body=data)
        return response

    def deploy(self, timeout=180):
        self.log.debug('Deploying the configuration.')

        url = self.base_url + '/operational/deploy'
        headers = self._get_auth_headers()

        self.log.debug('Sending the request to deploy the configuration.')
        response = self._send_request(url, method='post', headers=headers)

        self.log.debug('Waiting for deploy job to finish.')
        state = response['state']
        if state == 'QUEUED':
            deploy_url = response['links']['self']
            current_time = datetime.datetime.now()
            end_time = current_time + datetime.timedelta(seconds=timeout)
            deployed = False
            while datetime.datetime.now() < end_time:
                self.log.debug('Checking the status of the deploy job.')
                response = self._send_request(deploy_url, headers=headers)
                state = response['state']
                self.log.debug(f'The state of the deploy job is {state}.')
                if state == 'DEPLOYED':
                    deployed = True
                    break
                time.sleep(5)
            if not deployed:
                raise Exception('Error while deploying the configuration.')
        else:
            raise Exception('Error occurred when requesting the '
                            'configuration deployment.')
