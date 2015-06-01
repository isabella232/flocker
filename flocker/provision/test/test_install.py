# Copyright Hybrid Logic Ltd.  See LICENSE file for details.

"""
Tests for ``flocker.provision._install``.
"""

from twisted.trial.unittest import SynchronousTestCase

from .. import PackageSource
from .._install import (
    task_install_flocker,
    CLUSTERHQ_REPO,
    run, put,
    get_repository_url, UnsupportedDistribution,
)
from .._effect import sequence


class GetRepositoryURL(SynchronousTestCase):
    """
    Tests for ``get_repository_url``.
    """

    def test_fedora_20(self):
        """
        It is possible to get a repository URL for Fedora 20 packages.
        """
        expected = ("https://clusterhq-archive.s3.amazonaws.com/fedora/"
                    "clusterhq-release$(rpm -E %dist).noarch.rpm")

        self.assertEqual(
            get_repository_url(
                distribution='fedora-20',
                flocker_version='0.3.0'),
            expected
        )

    def test_centos_7(self):
        """
        It is possible to get a repository URL for CentOS 7 packages.
        """
        expected = ("https://clusterhq-archive.s3.amazonaws.com/centos/"
                    "clusterhq-release$(rpm -E %dist).noarch.rpm")

        self.assertEqual(
            get_repository_url(
                distribution='centos-7',
                flocker_version='0.3.0'),
            expected
        )

    def test_ubuntu_14_04(self):
        """
        It is possible to get a repository URL for Ubuntu 14.04 packages.
        """
        expected = ("https://clusterhq-archive.s3.amazonaws.com/ubuntu/14.04"
                    "/$(ARCH)")

        self.assertEqual(
            get_repository_url(
                distribution='ubuntu-14.04',
                flocker_version='0.3.0'),
            expected
        )

    def test_unsupported_distribution(self):
        """
        An ``UnsupportedDistribution`` error is thrown if a repository for the
        desired distribution cannot be found.
        """
        self.assertRaises(
            UnsupportedDistribution,
            get_repository_url, 'fedora-20', '0.3.0',
        )

    def test_non_release(self):
        """
        Operating system keys have the suffix ``-testing`` for non-marketing
        releases.
        """
        expected = ("https://clusterhq-archive.s3.amazonaws.com/"
                    "fedora-testing/"
                    "clusterhq-release$(rpm -E %dist).noarch.rpm")

        self.assertEqual(
            get_repository_url(
                distribution='fedora-20',
                flocker_version='0.3.0dev1'),
            expected
        )

class InstallFlockerTests(SynchronousTestCase):
    """
    Tests for ``task_install_flocker``.
    """

    def test_centos_no_arguments(self):
        """
        With no arguments, ``task_install_flocker`` installs the latest
        release.
        """
        distribution = 'centos-7'
        commands = task_install_flocker(distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command="yum install -y %s" % CLUSTERHQ_REPO[distribution]),
            run(command="yum install -y clusterhq-flocker-node")
        ]))

    def test_centos_with_version(self):
        """
        With a ``PackageSource`` containing just a version,
        ``task_install_flocker`` installs that version from our release
        repositories.
        """
        distribution = 'centos-7'
        source = PackageSource(os_version="1.2.3-1")
        commands = task_install_flocker(
            package_source=source,
            distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command="yum install -y %s" % CLUSTERHQ_REPO[distribution]),
            run(command="yum install -y clusterhq-flocker-node-1.2.3-1")
        ]))

    def test_ubuntu_no_arguments(self):
        """
        With no arguments, ``task_install_flocker`` installs the latest
        release.
        """
        distribution = 'ubuntu-14.04'
        commands = task_install_flocker(distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command='apt-get -y install apt-transport-https software-properties-common'),  # noqa
            run(command='add-apt-repository -y ppa:james-page/docker'),
            run(command="add-apt-repository -y 'deb {} /'".format(CLUSTERHQ_REPO[distribution])),  # noqa
            run(command='apt-get update'),
            run(command='apt-get -y --force-yes install clusterhq-flocker-node'),  # noqa
        ]))

    def test_ubuntu_with_version(self):
        """
        With a ``PackageSource`` containing just a version,
        ``task_install_flocker`` installs that version from our release
        repositories.
        """
        distribution = 'ubuntu-14.04'
        source = PackageSource(os_version="1.2.3-1")
        commands = task_install_flocker(
            package_source=source,
            distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command='apt-get -y install apt-transport-https software-properties-common'),  # noqa
            run(command='add-apt-repository -y ppa:james-page/docker'),
            run(command="add-apt-repository -y 'deb {} /'".format(CLUSTERHQ_REPO[distribution])),  # noqa
            run(command='apt-get update'),
            run(command='apt-get -y --force-yes install clusterhq-flocker-node=1.2.3-1'),  # noqa
        ]))

    def test_ubuntu_with_branch(self):
        """
        With a ``PackageSource`` containing just a branch,
        ``task_install_flocker`` installs that version from buildbot.
        """
        distribution = 'ubuntu-14.04'
        source = PackageSource(branch="branch-FLOC-1234")
        commands = task_install_flocker(
            package_source=source,
            distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command='apt-get -y install apt-transport-https software-properties-common'),  # noqa
            run(command='add-apt-repository -y ppa:james-page/docker'),
            run(command="add-apt-repository -y 'deb {} /'".format(CLUSTERHQ_REPO[distribution])),  # noqa
            run(command="add-apt-repository -y "
                        "'deb http://build.clusterhq.com/results/omnibus/branch-FLOC-1234/ubuntu-14.04 /'"),  # noqa
            put(
                content='Package:  *\nPin: origin build.clusterhq.com\nPin-Priority: 900\n',  # noqa
                path='/etc/apt/preferences.d/buildbot-900'),
            run(command='apt-get update'),
            run(command='apt-get -y --force-yes install clusterhq-flocker-node'),  # noqa
        ]))

    def test_with_branch(self):
        """
        With a ``PackageSource`` containing just a branch,
        ``task_install_flocker`` installs the latest build of the branch from
        our build server.
        """
        distribution = 'centos-7'
        source = PackageSource(branch="branch")
        commands = task_install_flocker(
            package_source=source,
            distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command="yum install -y %s" % CLUSTERHQ_REPO[distribution]),
            put(content="""\
[clusterhq-build]
name=clusterhq-build
baseurl=http://build.clusterhq.com/results/omnibus/branch/centos-7
gpgcheck=0
enabled=0
""",
                path="/etc/yum.repos.d/clusterhq-build.repo"),
            run(command="yum install --enablerepo=clusterhq-build "
                        "-y clusterhq-flocker-node")
        ]))

    def test_with_server(self):
        """
        With a ``PackageSource`` containing a branch and build server,
        ``task_install_flocker`` installs the latest build of the branch from
        that build server.
        """
        distribution = "centos-7"
        source = PackageSource(branch="branch",
                               build_server='http://nowhere.example/')
        commands = task_install_flocker(
            package_source=source,
            distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command="yum install -y %s" % CLUSTERHQ_REPO[distribution]),
            put(content="""\
[clusterhq-build]
name=clusterhq-build
baseurl=http://nowhere.example/results/omnibus/branch/centos-7
gpgcheck=0
enabled=0
""",
                path="/etc/yum.repos.d/clusterhq-build.repo"),
            run(command="yum install --enablerepo=clusterhq-build "
                        "-y clusterhq-flocker-node")
        ]))

    def test_with_branch_and_version(self):
        """
        With a ``PackageSource`` containing a branch and version,
        ``task_install_flocker`` installs the specifed build of the branch from
        that build server.
        """
        distribution = "centos-7"
        source = PackageSource(branch="branch", os_version='1.2.3-1')
        commands = task_install_flocker(
            package_source=source,
            distribution=distribution)
        self.assertEqual(commands, sequence([
            run(command="yum install -y %s" % CLUSTERHQ_REPO[distribution]),
            put(content="""\
[clusterhq-build]
name=clusterhq-build
baseurl=http://build.clusterhq.com/results/omnibus/branch/centos-7
gpgcheck=0
enabled=0
""",
                path="/etc/yum.repos.d/clusterhq-build.repo"),
            run(command="yum install --enablerepo=clusterhq-build "
                        "-y clusterhq-flocker-node-1.2.3-1")
        ]))
