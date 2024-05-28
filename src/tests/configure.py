import zaza.model as zaza_model

def setup_osd_standalone():
    """Perform the necessary steps to setup a single OSD."""
    cmds = ['sudo ceph osd crush rule rm replicated_rule',
            'sudo ceph osd crush rule create-replicated replicated_rule '
            'default osd',
            'sudo ceph osd erasure-code-profile rm default',
            'sudo ceph osd erasure-code-profile set default '
            'plugin=jerasure k=2 m=1 crush-failure-domain=osd']
    for cmd in cmds:
        zaza_model.run_on_unit('ceph-mon/0', cmd)

    loops = []
    for file in ('l1', 'l2', 'l3'):
        zaza_model.run_on_unit('ceph-osd/0', 'touch %s' % file)
        zaza_model.run_on_unit('ceph-osd/0', 'truncate --size 2G ./%s' % file)
        out = zaza_model.run_on_unit('ceph-osd/0',
                                     'sudo losetup -fP --show ./%s' % file)
        loops.append(out['Stdout'].strip())

    for loop in loops:
        zaza_model.run_action_on_leader('ceph-osd', 'add-disk',
                                        action_params={'osd-devices': loop})

    states = None
    try:
        zaza_model.get_application('ubuntu')
        states = {'ubuntu': {'workload-status-message': ''}}
    except KeyError:
        pass

    zaza_model.wait_for_application_states(states=states)
