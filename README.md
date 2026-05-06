[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/mtakemi/ros2_template_py)

# ros2_template_py


## ビルド

```bash
cd ~/unitree_ws
colcon build --packages-select ros2_template_py
source install/setup.bash
```


## 実行方法

```bash

ros2 run ros2_template_py simple_publisher

ros2 run ros2_template_py simple_subscriber

ros2 launch ros2_template_py lifecycle_pubsub.launch.py

```

## lifecycle_* 状態遷移図

`ros2_template_py/lifecycle_*` の状態遷移は以下です。

```mermaid
stateDiagram-v2
	[*] --> unconfigured
	unconfigured --> inactive: configure
	inactive --> active: activate
	active --> inactive: deactivate
	inactive --> unconfigured: cleanup

	unconfigured --> finalized: shutdown
	inactive --> finalized: shutdown
	active --> finalized: shutdown
```

使用コマンド例:

```bash
ros2 lifecycle set /lifecycle_publisher activate
ros2 lifecycle set /lifecycle_publisher deactivate
ros2 lifecycle set /lifecycle_publisher cleanup
ros2 lifecycle set /lifecycle_publisher shutdown
ros2 lifecycle get /lifecycle_publisher
```


## state_machine_node 状態遷移図

`ros2_template_py/state_machine_node.py` の状態遷移は以下です。

```mermaid
stateDiagram-v2
	[*] --> INIT
	INIT --> MOVE: next
	MOVE --> MODE1: next
	MODE1 --> MODE2: next
	MODE2 --> RETURN: next

	INIT --> INIT: reset
	MOVE --> INIT: reset
	MODE1 --> INIT: reset
	MODE2 --> INIT: reset
	RETURN --> INIT: reset
```

使用コマンド例:

```bash
ros2 service call /state_machine_node/next std_srvs/srv/Trigger "{}"
ros2 service call /state_machine_node/reset std_srvs/srv/Trigger "{}"
ros2 param set /state_machine_node target_state MODE2
```

## sm_example_node 状態遷移図

`ros2_template_py/sm_example_node.py` の状態遷移は以下です。

```mermaid
stateDiagram-v2
		[*] --> IDLE
		IDLE --> CHECKING: start
		CHECKING --> WORKING: check_ok
		CHECKING --> IDLE: check_fail
		WORKING --> DONE: finish
		DONE --> IDLE: reset
```

使用トリガ例:

```bash
ros2 param set /sm_example_node fire_trigger start
ros2 param set /sm_example_node fire_trigger finish
ros2 param set /sm_example_node fire_trigger reset
```

