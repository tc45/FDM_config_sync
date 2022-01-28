import argparse
import logging
import yaml
from fdm import FDMClient


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", help="Path to the configuration file", default="fdm.cfg")
    parser.add_argument("--debug", "-d", help="Display debug logs", action="store_true")

    return parser.parse_args()


def init_logger(log_level=logging.INFO):
    log = logging.getLogger(__file__)
    log.setLevel(log_level)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)
    return log


class ConfigSync:

    def __init__(self, config, log):
        self.log = log
        self.config_file = config
        self.log.info('Initializing ConfigSync class.')
        self.config = self._parse_config(config)
        self.fdm = self._init_fdm_client(self.config)
        self.log.debug('configSync class initialization finished.')

    def _parse_config(self, config_file):
        self.log.info('parsing the configuration file.')
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.log.debug(f'The following parameters were received: {config}')
        return config

    def _init_fdm_client(self, config):
        self.log.info('Initializing FDMClient class.')
        host = config.get('fdm_host')
        username = config.get('fdm_username')
        password = config.get('fdm_password')
        print(f'Username is {username} and password is {password}')
        fdm = FDMClient(host, username=username, password=password, log=self.log)
        self.log.info('Login to FDM.')
        fdm.login()
        return fdm

    def _get_url_category(self, name):
        category_dict = None
        for category in self.url_categories:
            category_name = category['name']
            if category_name == name:
                category_dict = {
                    'urlCategory': {
                        'name': category_name,
                        'id': category['id'],
                        'type': category['type']
                    },
                    'type': 'urlcategorymatcher'
                }
                break
        return category_dict

    def get_config(self):
        access_rule_name = self.config['url_filtering']['rule_name']
        self.log.info('Requesting access rule for URL filtering from FDM.')
        self.access_rule = self.fdm.get_access_rule_by_name(access_rule_name)

    def sync(self):
        self.log.info('starting the config sync.')
        self.log.info('Requesting URL categories from FDM.')
        self.url_categories = self.fdm.get_url_categories()
        self.access_rule['urlFilter']['urlCategories'] = []
        self.log.info('Updating the access rule.')
        for category in self.config['url_filtering']['url_categories']:
            cat_dict = self._get_url_category(category)
            if cat_dict:
                self.access_rule['urlFilter']['urlCategories'].append(cat_dict)
        self.log.info('Adding the configuration to FDM.')
        self.fdm.put_access_rule(self.access_rule)

    def deploy(self):
        self.log.info('Starting with the configuration deployment.')
        self.fdm.deploy()
        self.log.info('Configuration deployment successful.')
        self.log.info('Logging out of the FDM.')
        self.fdm.logout()


if __name__ == "__main__":
    args = parse_arguments()

    if args.debug:
        log = init_logger(logging.DEBUG)
    else:
        log = init_logger()

    cs = ConfigSync(config=args.config, log=log)
    # print(cs.fdm.token)
    cs.get_config()
    cs.sync()
    cs.deploy()
