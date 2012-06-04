#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from itertools import product
from argparse import REMAINDER

from chroma_cli.output import StandardFormatter
from chroma_cli.exceptions import InvalidVolumeNode, TooManyMatches, BadUserInput, NotFound


class Dispatcher(object):
    def __init__(self):
        self.build_handler_map()

    def __call__(self, key):
        try:
            return self.handlers[key]
        except KeyError:
            raise RuntimeError("Unhandled action: %s" % key)

    def build_handler_map(self):
        self.handlers = {}
        # NB: This only handles a single level of subclasses.
        for cls in Handler.__subclasses__():
            for key in cls.primary_actions():
                if key in self.handlers:
                    raise RuntimeError("Handler collision: %s:%s -> %s:%s" %
                                       (cls, key, self.handlers[key], key))
                else:
                    self.handlers[key] = cls

    @property
    def handled_actions(self):
        return sorted(self.handlers.keys())


class Handler(object):
    nouns = []
    secondary_nouns = []
    verbs = ["show", "list", "add", "remove"]
    intransitive_verbs = ["list"]

    @classmethod
    def noun_verbs(cls):
        return ["%s-%s" % t for t in product(*[cls.nouns, cls.verbs])]

    @classmethod
    def primary_actions(cls):
        return cls.nouns + cls.noun_verbs()

    @property
    def secondary_actions(self):
        return ["%s-%s" % t for t in product(*[self.secondary_nouns, self.verbs])]

    @property
    def subject_name(self):
        return self.nouns[0]

    def __init__(self, api, formatter=None):
        self.api = api

        self.output = formatter
        if not self.output:
            self.output = StandardFormatter()

        self.errors = []

    def __call__(self, parser, namespace, args=None):
        ns = namespace
        parser.reset()

        try:
            ns.noun, ns.verb = ns.primary_action.split("-")
            parser.add_argument("primary_action",
                                choices=self.noun_verbs())
            if ns.verb not in self.intransitive_verbs:
                parser.add_argument("subject", help=self.subject_name)
            parser.clear_resets()
            parser.add_argument("options", nargs=REMAINDER)
            ns = parser.parse_args(args, ns)
        except ValueError:
            parser.add_argument("noun", choices=self.nouns)
            parser.add_argument("subject", help=self.subject_name)
            parser.add_argument("secondary_action",
                                choices=self.secondary_actions)
            parser.add_argument("options", nargs=REMAINDER)
            ns = parser.parse_args(args)
            try:
                ns.secondary_noun, ns.verb = ns.secondary_action.split("-")
            except ValueError:
                # Irregular verb?
                ns.verb = ns.secondary_action

        if ns.verb == "add":
            parser.reset()
            self._api_fields_to_parser_args(parser)
            ns = parser.parse_args(args, ns)

        verb_method = getattr(self, ns.verb)
        verb_method(ns)

    def _api_fields_to_parser_args(self, parser):
        for name, attrs in self.api_endpoint.fields.items():
            if attrs['readonly']:
                continue

            kwargs = {'help': attrs['help_text']}
            if attrs['type'] in ["related", "list"]:
                kwargs['action'] = "append"
                kwargs['type'] = str
            elif attrs['type'] == "boolean":
                kwargs['action'] = "store_true"
                kwargs['default'] = False
            elif attrs['type'] == "integer":
                kwargs['type'] = int

            parser.add_argument("--%s" % name, **kwargs)

    def _resolve_volume_node(self, spec):
        try:
            hostname, path = spec.split(":")
            host = self.api.endpoints['host'].show(hostname)
            kwargs = {'host': host['id'], 'path': path}
            vn_set = self.api.endpoints['volume_node'].list(**kwargs)
            if len(vn_set) > 1:
                raise TooManyMatches()
            else:
                return vn_set[0]
        except (ValueError, IndexError):
            raise InvalidVolumeNode(spec)

    def _resolve_volume_nodes(self, specs):
        vn_list = []
        for spec in specs.split(","):
            vn_list.append(self._resolve_volume_node(spec))
        return vn_list

    def list(self, ns):
        self.output(self.api_endpoint.list())

    def show(self, ns):
        self.output(self.api_endpoint.show(ns.subject))

    def remove(self, ns):
        self.output(self.api_endpoint.delete(ns.subject))


class ServerHandler(Handler):
    nouns = ["server", "srv", "mgs", "mds", "oss"]
    secondary_nouns = ["target", "tgt", "mgt", "mdt", "ost", "volume", "vol"]
    lnet_actions = ["lnet-stop", "lnet-start", "lnet-load", "lnet-unload"]
    subject_name = "hostname"

    def __init__(self, *args, **kwargs):
        super(ServerHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['host']
        for action in self.lnet_actions:
            # NB: This will break if we ever want to add more secondary
            # actions with the same verbs to this handler.
            verb = action.split("-")[1]
            self.__dict__[verb] = self.set_lnet_state

    @property
    def secondary_actions(self):
        return self.lnet_actions + super(ServerHandler, self).secondary_actions

    def set_lnet_state(self, ns):
        lnet_state = {'stop': "lnet_down",
                      'start': "lnet_up",
                      'unload': "lnet_unloaded",
                      'load': "lnet_down"}
        kwargs = {'state': lnet_state[ns.verb]}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def list(self, ns):
        try:
            host = self.api_endpoint.show(ns.subject)
            kwargs = {'host_id': host['id']}
            if '--primary' in ns.options:
                kwargs['primary'] = True

            if ns.secondary_noun in ["ost", "mdt", "mgt"]:
                kwargs['kind'] = ns.secondary_noun
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.secondary_noun in ["target", "tgt"]:
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.secondary_noun in ["volume", "vol"]:
                self.output(self.api.endpoints['volume'].list(**kwargs))
        except AttributeError:
            kwargs = {}
            if ns.noun in ["mgs", "mds", "oss"]:
                kwargs['role'] = ns.noun
            self.output(self.api_endpoint.list(**kwargs))

    def add(self, ns):
        kwargs = {'address': ns.subject}
        self.output(self.api_endpoint.create(**kwargs))


class FilesystemHandler(Handler):
    nouns = ["filesystem", "fs"]
    secondary_nouns = ["target", "tgt", "mgt", "mdt", "ost", "volume", "vol", "server", "mgs", "mds", "oss"]
    verbs = ["list", "show", "add", "remove", "start", "stop", "detect"]

    @property
    def secondary_actions(self):
        return ["mountspec"] + super(FilesystemHandler, self).secondary_actions

    @property
    def intransitive_verbs(self):
        return ["detect"] + super(FilesystemHandler, self).intransitive_verbs

    def __init__(self, *args, **kwargs):
        super(FilesystemHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['filesystem']

    def stop(self, ns):
        kwargs = {'state': "stopped"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def start(self, ns):
        kwargs = {'state': "available"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def detect(self, ns):
        kwargs = {'message': "Detecting filesystems",
                  'jobs': [{'class_name': 'DetectTargetsJob', 'args': {}}]}
        self.output(self.api.endpoints['command'].create(**kwargs))

    def list(self, ns):
        try:
            fs = self.api_endpoint.show(ns.subject)
            kwargs = {'filesystem_id': fs['id']}
            if '--primary' in ns.options:
                kwargs['primary'] = True

            if ns.secondary_noun in ["ost", "mdt", "mgt"]:
                kwargs['kind'] = ns.secondary_noun
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.secondary_noun == "target":
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.secondary_noun == "server":
                self.output(self.api.endpoints['host'].list(**kwargs))
            elif ns.secondary_noun in ["oss", "mds", "mgs"]:
                kwargs['role'] = ns.secondary_noun
                self.output(self.api.endpoints['host'].list(**kwargs))
            elif ns.secondary_noun == "volume":
                self.output(self.api.endpoints['volume'].list(**kwargs))
        except AttributeError:
            self.output(self.api_endpoint.list())

    def _resolve_mgt(self, ns):
        if ns.mgt is None:
            raise BadUserInput("No MGT supplied.")

        if len(ns.mgt) > 1:
            raise BadUserInput("Only 1 MGT per filesystem is allowed.")

        mgt = {}
        try:
            mgt_vn = self._resolve_volume_node(ns.mgt[0])
            mgt['volume_id'] = mgt_vn.volume_id
        except (InvalidVolumeNode, NotFound):
            mgs = self.api.endpoints['host'].show(ns.mgt[0])
            kwargs = {'host_id': mgs['id'], 'kind': 'mgt'}
            try:
                mgt['id'] = self.api.endpoints['target'].list(**kwargs)[0]['id']
            except IndexError:
                raise BadUserInput("Invalid mgt spec: %s" % ns.mgt[0])
        return mgt

    def _resolve_mdt(self, ns):
        if ns.mdts is None:
            raise BadUserInput("No MDT supplied.")

        if len(ns.mdts) > 1:
            # NB: Following the API -- only 1 MDT supported for now.
            raise BadUserInput("Only 1 MDT per filesystem is supported.")

        mdt_vn = self._resolve_volume_node(ns.mdts[0])
        return {'conf_params': {}, 'volume_id': mdt_vn.volume_id}

    def _resolve_osts(self, ns):
        if ns.osts is None:
            raise BadUserInput("At least one OST must be supplied.")

        osts = []
        for ost_spec in ns.osts:
            ost_vn = self._resolve_volume_node(ost_spec)
            osts.append({'conf_params': {}, 'volume_id': ost_vn.volume_id})
        return osts

    def add(self, ns):
        # TODO: Adjust primary/failover relationships via CLI
        kwargs = {'conf_params': {}}
        kwargs['name'] = ns.subject
        kwargs['mgt'] = self._resolve_mgt(ns)
        kwargs['mdt'] = self._resolve_mdt(ns)
        kwargs['osts'] = self._resolve_osts(ns)
        self.output(self.api_endpoint.create(**kwargs))

    def mountspec(self, ns):
        fs = self.api_endpoint.show(ns.subject)
        self.output(fs['mount_path'])


class TargetHandler(Handler):
    nouns = ["target", "tgt", "mgt", "mdt", "ost"]
    verbs = ["list", "show", "add", "remove", "start", "stop"]

    def __init__(self, *args, **kwargs):
        super(TargetHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['target']

    def stop(self, ns):
        kwargs = {'state': "unmounted"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def start(self, ns):
        kwargs = {'state': "mounted"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def remove(self, ns):
        # HTTP DELETE doesn't seem to work -- some downcasting problem?
        kwargs = {'state': "removed"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def add(self, ns):
        vn = self._resolve_volume_node(ns.subject)
        kwargs = {'kind': ns.noun.upper(), 'volume_id': vn.volume_id}
        if ns.noun != 'mgt':
            fs = self.api.endpoints['filesystem'].show(ns.filesystem)
            kwargs['filesystem_id'] = fs.id

        self.output(self.api_endpoint.create(**kwargs))

    def list(self, ns):
        kwargs = {}
        if ns.noun in ["mgt", "mdt", "ost"]:
            kwargs['kind'] = ns.noun
        self.output(self.api_endpoint.list(**kwargs))


class VolumeHandler(Handler):
    nouns = ["volume", "vol"]
    verbs = ["list", "show"]

    def __init__(self, *args, **kwargs):
        super(VolumeHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['volume']
