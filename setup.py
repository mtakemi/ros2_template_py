from glob import glob
from setuptools import find_packages, setup

package_name = 'ros2_template_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='masafumi',
    maintainer_email='m.takemi@gmail.com',
    description='TODO: Package description',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'simple_publisher = ros2_template_py.simple_publisher:main',
            'simple_subscriber = ros2_template_py.simple_subscriber:main',
            'nav2_action_client = ros2_template_py.nav2_action_client:main',
            'lifecycle_publisher = ros2_template_py.lifecycle_publisher:main',
            'lifecycle_subscriber = ros2_template_py.lifecycle_subscriber:main',
            'state_machine_node = ros2_template_py.state_machine_node:main',
        ],
    },
)
