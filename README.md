# ROS 2 Minecraft Drone Patrol

Курсовой проект по дисциплине **«Основы мобильной робототехники»**.

Проект реализует ROS 2-систему автономного патрулирования виртуального дрона в Minecraft-среде. В качестве дрона используется отдельная Minecraft-сущность `Allay`, управляемая из ROS 2 через сервис `/minecraft/command`. Minecraft используется как 3D-среда-симулятор, а RViz2 — как инструмент визуализации карты, маршрута и состояния дрона.

## 1. Цель проекта

Цель работы — разработать учебную робототехническую систему, которая демонстрирует:

* создание виртуального полигона в Minecraft;
* управление отдельным объектом-дроном из ROS 2;
* построение 2D-карты занятости;
* планирование маршрута с помощью алгоритма A*;
* выполнение миссии по состояниям;
* визуализацию карты, маршрута и траектории в RViz2.

## 2. Итоговая демонстрация

В демонстрации система выполняет следующий сценарий:

1. Minecraft запускается с модом `minecraft_ros2`.
2. ROS 2 создаёт испытательный полигон: платформу, препятствия, waypoint-зоны и цель инспекции.
3. ROS 2 создаёт отдельного Allay-дрона.
4. `map_builder_node` строит 2D occupancy grid-карту.
5. `mission_planner_node` задаёт высокоуровневые цели миссии.
6. `path_planner_node` строит A* маршрут до текущей цели.
7. `drone_entity_controller_node` двигает Allay-дрона по маршруту.
8. `player_camera_follow_node` ведёт игрока-камеру за дроном.
9. RViz2 показывает карту, препятствия, A* путь, фактическую траекторию, цель и положение дрона.

## 3. Архитектура

```text
world_setup_node
  создаёт Minecraft-полигон, препятствия, цель и waypoint-зоны

drone_spawn_node
  создаёт отдельную Minecraft-сущность Allay с тегом ros_drone

map_builder_node
  строит 2D occupancy grid-карту известных препятствий
  публикует /drone/local_map

mission_planner_node
  реализует state machine:
  TAKEOFF → PATROL_REDSTONE → PATROL_EMERALD → PATROL_LAPIS
  → GO_TO_INSPECTION → INSPECT → RETURN_HOME → LAND → DONE
  публикует high-level goal в /drone/goal

path_planner_node
  читает /drone/local_map, /drone/pose и /drone/goal
  строит A* маршрут
  публикует /drone/planned_path и промежуточную /drone/target

drone_entity_controller_node
  читает /drone/target
  плавно двигает Allay через /minecraft/command
  публикует /drone/pose и /drone/path

player_camera_follow_node
  держит игрока-камеру рядом с дроном

visualizer_node
  публикует RViz-маркеры в /drone/markers

RViz2
  показывает карту, препятствия, путь, траекторию, цель и положение дрона
```

## 4. Используемые технологии

* Ubuntu 22.04
* ROS 2 Humble
* Python 3.10
* Minecraft Java Edition
* `minecraft_ros2`
* `ros2_java`
* Java 21
* RViz2
* ROS 2 topics, services, launch-файлы
* `nav_msgs/msg/OccupancyGrid`
* `nav_msgs/msg/Path`
* `geometry_msgs/msg/PoseStamped`
* `visualization_msgs/msg/MarkerArray`

## 5. Рабочие директории

```text
~/ros2_java_ws
~/minecraft_ros2
~/minecraft_drone_ws
```

Пакет курсового проекта:

```text
~/minecraft_drone_ws/src/minecraft_drone_coursework
```

## 6. Структура пакета

```text
minecraft_drone_coursework/
  minecraft_drone_coursework/
    world_setup_node.py
    drone_spawn_node.py
    drone_entity_controller_node.py
    mission_planner_node.py
    map_builder_node.py
    path_planner_node.py
    player_camera_follow_node.py
    sensor_monitor_node.py
    visualizer_node.py

  launch/
    full_mission_astar.launch.py
    astar_planner_test.launch.py
    map_builder.launch.py
    spawn_drone.launch.py

  config/
    patrol_params.yaml

  rviz/
    minecraft_drone.rviz

  package.xml
  setup.py
  README.md
```

## 7. Подготовка окружения

Проект рассчитан на связку:

```text
Ubuntu 22.04 + ROS 2 Humble
```

Проверка ROS 2:

```bash
source ~/.bashrc
echo $ROS_DISTRO
which ros2
```

Ожидаемо:

```text
humble
/opt/ros/humble/bin/ros2
```

Проверка Java:

```bash
java -version
javac -version
```

Ожидаемо:

```text
openjdk version "21..."
javac 21...
```

Проверка `ros2_java` и сообщений Minecraft:

```bash
echo $ROS2JAVA_INSTALL_PATH
ros2 pkg list | grep rcljava
ros2 pkg list | grep minecraft_msgs
```

Ожидаемо:

```text
/home/nikita/ros2_java_ws/install
rcljava
rcljava_common
minecraft_msgs
```

В `~/.bashrc` должны быть подключены ROS 2, `ros2_java` и workspace проекта:

```bash
source /opt/ros/humble/setup.bash

export ROS2JAVA_INSTALL_PATH=$HOME/ros2_java_ws/install
source $ROS2JAVA_INSTALL_PATH/setup.bash

export ROS_DOMAIN_ID=0

source ~/minecraft_drone_ws/install/setup.bash
```

## 8. Сборка проекта

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
colcon build
source install/setup.bash
```

Проверка исполняемых нод:

```bash
ros2 pkg executables minecraft_drone_coursework
```

Ожидаемые ноды:

```text
minecraft_drone_coursework world_setup_node
minecraft_drone_coursework drone_spawn_node
minecraft_drone_coursework drone_entity_controller_node
minecraft_drone_coursework mission_planner_node
minecraft_drone_coursework map_builder_node
minecraft_drone_coursework path_planner_node
minecraft_drone_coursework player_camera_follow_node
minecraft_drone_coursework sensor_monitor_node
minecraft_drone_coursework visualizer_node
```

## 9. Запуск Minecraft

Minecraft запускается из графического терминала Ubuntu:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

После запуска нужно зайти в мир Minecraft. Для проекта удобно использовать `Superflat`-мир в режиме `Creative` с включёнными cheats.

## 10. Проверка связи Minecraft ↔ ROS 2

В отдельном терминале:

```bash
source ~/.bashrc
ros2 topic list
ros2 service list
```

Ожидаемые топики:

```text
/cmd_vel
/player/ground_truth
/player/image_raw
/player/imu
/player/pointcloud
/player/surrounding_block_array
/tf
```

Ожидаемые сервисы:

```text
/minecraft/command
/spawn_entity
/dig_block
```

Проверка команды Minecraft:

```bash
ros2 service call /minecraft/command minecraft_msgs/srv/Command "{command: 'time set day'}"
```

Ожидаемый ответ:

```text
success=True
message='Success'
```

## 11. Полный запуск проекта

Убедиться, что Minecraft открыт и игрок находится внутри мира.

Запуск:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
ros2 launch minecraft_drone_coursework full_mission_astar.launch.py
```

Launch-файл запускает:

```text
world_setup_node
drone_spawn_node
map_builder_node
drone_entity_controller_node
path_planner_node
mission_planner_node
player_camera_follow_node
sensor_monitor_node
visualizer_node
rviz2
```

Ожидаемый результат:

* создаётся испытательный полигон;
* появляется Allay-дрон с именем `ROS Drone`;
* дрон выполняет миссию;
* камера следует за дроном;
* RViz2 показывает карту, препятствия, A* путь, фактическую траекторию, цель и позицию дрона.

## 12. Запуск по частям

Подготовить полигон:

```bash
ros2 run minecraft_drone_coursework world_setup_node
```

Создать Allay-дрона:

```bash
ros2 run minecraft_drone_coursework drone_spawn_node
```

Запустить карту:

```bash
ros2 run minecraft_drone_coursework map_builder_node
```

Запустить контроллер дрона:

```bash
ros2 run minecraft_drone_coursework drone_entity_controller_node
```

Запустить A* planner:

```bash
ros2 run minecraft_drone_coursework path_planner_node
```

Отправить цель вручную:

```bash
ros2 topic pub --once /drone/goal geometry_msgs/msg/PoseStamped "{header: {frame_id: 'map'}, pose: {position: {x: 19.0, y: 19.0, z: 10.0}, orientation: {w: 1.0}}}"
```

Запустить камеру:

```bash
ros2 run minecraft_drone_coursework player_camera_follow_node
```

Запустить RViz-маркеры:

```bash
ros2 run minecraft_drone_coursework visualizer_node
```

## 13. Основные топики проекта

```text
/drone/pose
/drone/path
/drone/target
/drone/goal
/drone/local_map
/drone/planned_path
/drone/status
/drone/mission_state
/drone/controller_status
/drone/planner_status
/drone/map_status
/drone/camera_status
/drone/sensor_status
/drone/visualizer_status
/drone/markers
```

## 14. Основной сервис

```text
/minecraft/command
```

Он используется для подготовки мира, создания дрона и перемещения Allay-сущности.

## 15. Mission state machine

`mission_planner_node` реализует следующую последовательность состояний:

```text
WAIT_FOR_DRONE
→ TAKEOFF
→ PATROL_REDSTONE
→ PATROL_EMERALD
→ PATROL_LAPIS
→ GO_TO_INSPECTION
→ INSPECT
→ RETURN_HOME
→ LAND
→ DONE
```

Mission planner не управляет дроном напрямую. Он публикует смысловую цель в `/drone/goal`, после чего `path_planner_node` строит A* маршрут и публикует промежуточную цель в `/drone/target`.

## 16. Алгоритм A*

`path_planner_node` строит маршрут на 2D occupancy grid-карте.

Вход:

```text
/drone/local_map
/drone/pose
/drone/goal
```

Выход:

```text
/drone/planned_path
/drone/target
/drone/planner_status
```

Клетки карты:

```text
0   — свободно
100 — занято
```

Планировщик использует 8-связную сетку и евклидову эвристику. Для диагональных переходов запрещено срезание углов рядом с препятствиями.

## 17. RViz2

RViz2 запускается автоматически из `full_mission_astar.launch.py`.

Конфиг:

```text
rviz/minecraft_drone.rviz
```

В RViz2 отображаются:

```text
/drone/local_map       — карта занятости
/drone/planned_path    — A* путь
/drone/path            — фактическая траектория
/drone/markers         — дрон, цели, waypoint-точки, препятствия
```

Если RViz2 открывается вручную:

```bash
rviz2 -d ~/minecraft_drone_ws/src/minecraft_drone_coursework/rviz/minecraft_drone.rviz
```

## 18. Мониторинг

Состояние миссии:

```bash
ros2 topic echo /drone/mission_state
```

Статус mission planner:

```bash
ros2 topic echo /drone/status
```

Статус A* planner:

```bash
ros2 topic echo /drone/planner_status
```

Текущий путь:

```bash
ros2 topic echo --once /drone/planned_path
```

Позиция дрона:

```bash
ros2 topic echo /drone/pose
```

Статус камеры:

```bash
ros2 topic echo /drone/camera_status
```

## 19. Запись rosbag

```bash
mkdir -p ~/minecraft_drone_bags
cd ~/minecraft_drone_bags

ros2 bag record \
  /drone/pose \
  /drone/path \
  /drone/goal \
  /drone/target \
  /drone/planned_path \
  /drone/local_map \
  /drone/status \
  /drone/mission_state \
  /drone/planner_status \
  /drone/markers
```

Остановить запись:

```text
Ctrl + C
```

## 20. Сценарий демонстрации

1. Запустить Minecraft:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

2. Зайти в Superflat-мир.

3. Запустить проект:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
ros2 launch minecraft_drone_coursework full_mission_astar.launch.py
```

4. Показать в Minecraft:

   * полигон;
   * препятствия;
   * Allay-дрона;
   * движение дрона;
   * камеру, следующую за дроном.

5. Показать в RViz2:

   * occupancy grid;
   * препятствия;
   * planned path;
   * actual path;
   * current goal;
   * current target.

6. Показать терминалы мониторинга:

```bash
ros2 topic echo /drone/mission_state
ros2 topic echo /drone/planner_status
```

## 21. Ограничения

* Физика дрона не моделируется.
* Allay перемещается через команды Minecraft `tp`.
* Карта строится по заранее известным препятствиям.
* Полноценный SLAM/Nav2 не используется.
* Препятствия считаются 2D no-fly зонами на карте.
* Сенсоры `minecraft_ros2` относятся к игроку, а не к Allay-сущности.

## 22. Возможные улучшения

* Выбор миссии через YAML.
* Ручная постановка цели через RViz2.
* Emergency stop.
* Запись и анализ rosbag.
* Построение карты по `/player/surrounding_block_array`.
* Сравнение прямого маршрута и A* маршрута.
* Метрики длины пути, времени миссии и числа перепланирований.

## 23. Быстрые команды

Запуск Minecraft:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

Запуск проекта:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
ros2 launch minecraft_drone_coursework full_mission_astar.launch.py
```

Мониторинг миссии:

```bash
ros2 topic echo /drone/mission_state
```

Мониторинг A*:

```bash
ros2 topic echo /drone/planner_status
```

Вернуть игрока в creative:

```bash
ros2 service call /minecraft/command minecraft_msgs/srv/Command "{command: 'gamemode creative @p'}"
```
