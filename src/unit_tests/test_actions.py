import sys

sys.path.append('actions')
import unittest
from mock import patch, MagicMock

__author__ = 'Chris Holcombe <chris.holcombe@canonical.com>'

# import get_quota as get_quota
# import remove_quota as remove_quota
# import set_quota as set_quota


def action_get_side_effect(*args):
    print 'args: {}'.format(args)
    if args[0] == 'max-files':
        return '1024'
    elif args[0] == 'max-bytes':
        return '1024'
    elif args[0] == 'directory':
        return 'foo'


class CephActionsTestCase(unittest.TestCase):
    def setUp(self):
        """
        It's patching time
        """
        self.charmhelpers_mock = MagicMock()
        self.charmhelpers_core_mock = MagicMock()
        self.charmhelpers_core_hookenv_mock = MagicMock()
        self.xattr_mock = MagicMock()
        modules = {
            'charmhelpers': self.charmhelpers_mock,
            'charmhelpers.core': self.charmhelpers_core_mock,
            'charmhelpers.core.hookenv': self.charmhelpers_core_hookenv_mock,
            'xattr': self.xattr_mock,
        }

        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()
        from get_quota import get_quota

        self.get_quota = get_quota

    def tearDown(self):
        """
        Let's clean up
        """
        self.module_patcher.stop()

    @patch('get_quota.action_get')
    @patch('get_quota.os')
    def test_get_quota(self, os, action_get):
        action_get.side_effect = action_get_side_effect()
        os.path.exists.return_value = True
        self.xattr_mock.getxattr.return_value = "1024"
        self.get_quota()
        self.xattr_mock.getxattr.assert_called_with('foo',
                                                    'ceph.quota.max_files')
        self.action_set.assert_called_with({'foo quota': "1024"})

    '''
    @patch.object(self, ceph_hooks, 'config')
    def test_set_quota():
        set_quota()
        self.assertEqual(foo, bar)

    @patch.object(self, ceph_hooks, 'config')
    def test_remove_quota():
        remove_quota()
        self.assertEqual(foo, bar)
    '''
