# ROS 2 Minecraft Drone Patrol

Курсовой проект по дисциплине **«Основы мобильной робототехники»**.

Проект реализует ROS 2-систему автономного патрулирования виртуального дрона в Minecraft-среде. В качестве виртуального дрона используется отдельная Minecraft-сущность `Allay`, которая управляется из ROS 2 через сервис `/minecraft/command`. Minecraft используется как простая 3D-среда-симулятор, а RViz2 — как робототехническая визуализация карты, маршрута и состояния дрона.

## 1. Краткое описание проекта

Цель проекта — разработать учебную ROS 2-систему, которая демонстрирует базовые принципы мобильной робототехники:

* подготовка симуляционной среды;
* создание отдельного виртуального агента-дрона;
* построение 2D-карты занятости;
* планирование маршрута с помощью алгоритма A*;
* выполнение миссии по состояниям;
* визуализация карты, траектории и целей в RViz2;
* сопровождение полёта камерой в Minecraft.

Итоговая демонстрация:

1. Minecraft запускается с модом `minecraft_ros2`.
2. ROS 2 создаёт испытательный полигон: платформу, препятствия, waypoint-зоны и цель инспекции.
3. ROS 2 создаёт отдельного Allay-дрона.
4. `map_builder_node` строит 2D occupancy grid-карту препятствий.
5. `mission_planner_node` задаёт смысловые цели миссии.
6. `path_planner_node` строит A* маршрут до текущей цели.
7. `drone_entity_controller_node` двигает Allay-дрона по маршруту.
8. `player_camera_follow_node` ведёт игрока-камеру за дроном.
9. RViz2 показывает карту, препятствия, A* путь, фактическую траекторию, текущую цель и положение дрона.

## 2. Архитектура системы

Общая схема:

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
  публикует RViz-маркеры:
  /drone/markers

RViz2
  показывает карту, препятствия, маршрут, фактическую траекторию и состояние дрона
```

## 3. Используемые технологии

* Ubuntu 22.04.5 LTS
* ROS 2 Humble
* Python 3.10
* Minecraft Java Edition через `minecraft_ros2`
* `ros2_java`
* Java 21
* Gradle / Forge
* RViz2
* ROS 2 topics, services, launch-файлы
* `nav_msgs/msg/OccupancyGrid`
* `nav_msgs/msg/Path`
* `geometry_msgs/msg/PoseStamped`
* `visualization_msgs/msg/MarkerArray`

## 4. Репозитории

Основные внешние репозитории:

```text
https://github.com/GeBondar/mobile-robotics-basics
https://github.com/minecraft-ros2/minecraft_ros2
```

Рабочие директории на виртуальной машине:

```text
~/ros2_java_ws
~/minecraft_ros2
~/minecraft_drone_ws
```

Пакет курсового проекта:

```text
~/minecraft_drone_ws/src/minecraft_drone_coursework
```

## 5. Важное замечание по версии Ubuntu

Для данного проекта используется:

```text
Ubuntu 22.04 + ROS 2 Humble
```

Не рекомендуется обновлять виртуальную машину до Ubuntu 24.04, потому что `minecraft_ros2` и `ros2_java` стабильнее работают в связке Ubuntu 22.04 + Humble.

## 6. Подготовка окружения

### 6.1. Проверка Ubuntu

```bash
lsb_release -a
uname -m
```

Ожидаемо:

```text
Ubuntu 22.04.x LTS
aarch64
```

### 6.2. Проверка ROS 2

```bash
source ~/.bashrc
echo $ROS_DISTRO
which ros2
ros2 --help | head
```

Ожидаемо:

```text
humble
/opt/ros/humble/bin/ros2
```

### 6.3. Проверка Java

```bash
java -version
javac -version
```

Ожидаемо:

```text
openjdk version "21..."
javac 21...
```

### 6.4. Проверка `ros2_java`

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

В `~/.bashrc` должны быть строки:

```bash
source /opt/ros/humble/setup.bash

export ROS2JAVA_INSTALL_PATH=$HOME/ros2_java_ws/install
source $ROS2JAVA_INSTALL_PATH/setup.bash

export ROS_DOMAIN_ID=0

source ~/minecraft_drone_ws/install/setup.bash
```

Если топики Minecraft пропали и видны только `/rosout` и `/parameter_events`, нужно проверить, что `ros2_java_ws` действительно подключён:

```bash
source ~/.bashrc
echo $ROS2JAVA_INSTALL_PATH
ros2 pkg list | grep minecraft_msgs
```

## 7. Особенности запуска Minecraft на ARM64 VM

Виртуальная машина работает на ARM64/aarch64. Для запуска Minecraft/Forge потребовалась доработка `~/minecraft_ros2/build.gradle`, чтобы подтянуть LWJGL natives для ARM64 Linux:

```gradle
/*
 * ARM64 Linux fix for running Minecraft/Forge inside aarch64 Ubuntu VM.
 * The default Minecraft dependencies pull LWJGL natives-linux,
 * but on Apple Silicon / ARM64 Linux we need natives-linux-arm64.
 */
def lwjglArm64Version = "3.3.3"

dependencies {
    runtimeOnly "org.lwjgl:lwjgl:${lwjglArm64Version}:natives-linux-arm64"
    runtimeOnly "org.lwjgl:lwjgl-glfw:${lwjglArm64Version}:natives-linux-arm64"
    runtimeOnly "org.lwjgl:lwjgl-opengl:${lwjglArm64Version}:natives-linux-arm64"
    runtimeOnly "org.lwjgl:lwjgl-openal:${lwjglArm64Version}:natives-linux-arm64"
    runtimeOnly "org.lwjgl:lwjgl-stb:${lwjglArm64Version}:natives-linux-arm64"
    runtimeOnly "org.lwjgl:lwjgl-freetype:${lwjglArm64Version}:natives-linux-arm64"
    runtimeOnly "org.lwjgl:lwjgl-jemalloc:${lwjglArm64Version}:natives-linux-arm64"
    runtimeOnly "org.lwjgl:lwjgl-tinyfd:${lwjglArm64Version}:natives-linux-arm64"
}
```

Также был отключён ранний Forge splash screen:

```bash
cd ~/minecraft_ros2
grep -n "earlyWindowControl" run/config/fml.toml
```

Должно быть:

```text
earlyWindowControl = false
```

Если нужно исправить:

```bash
sed -i 's/earlyWindowControl = true/earlyWindowControl = false/' ~/minecraft_ros2/run/config/fml.toml
```

## 8. Структура ROS 2-пакета

```text
minecraft_drone_coursework/
  minecraft_drone_coursework/
    __init__.py
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
    entity_drone_patrol.launch.py

  config/
    patrol_params.yaml

  rviz/
    minecraft_drone.rviz

  package.xml
  setup.py
  README.md
```

## 9. Описание ROS 2-нод

### 9.1. `world_setup_node`

Готовит Minecraft-полигон через сервис:

```text
/minecraft/command
```

Создаёт:

* ровную платформу;
* границы полигона;
* стартовую зону;
* waypoint-зоны;
* inspection target;
* набор препятствий;
* удобные игровые настройки.

Основные действия:

```text
time set day
weather clear
difficulty peaceful
gamerule doMobSpawning false
gamerule doDaylightCycle false
gamerule doWeatherCycle false
gamemode creative @p
fill ...
```

Важно: `world_setup_node` удаляет старого дрона с тегом `ros_drone`, поэтому после ручного запуска этой ноды нужно заново запускать `drone_spawn_node`.

### 9.2. `drone_spawn_node`

Создаёт отдельного Allay-дрона:

```text
minecraft:allay
```

Дрон получает тег:

```text
ros_drone
```

И имя:

```text
ROS Drone
```

Allay создаётся с параметрами:

* `NoAI:1b`
* `NoGravity:1b`
* `Invulnerable:1b`
* `Glowing:1b`
* `CustomNameVisible:1b`

### 9.3. `drone_entity_controller_node`

Низкоуровневый контроллер дрона.

Подписывается на:

```text
/drone/target
```

Публикует:

```text
/drone/pose
/drone/path
/drone/controller_status
```

Двигает Allay-дрона через Minecraft-команду:

```text
tp @e[tag=ros_drone,limit=1,sort=nearest] x y z
```

### 9.4. `map_builder_node`

Строит 2D occupancy grid-карту полигона на основе заранее известных препятствий.

Публикует:

```text
/drone/local_map
/drone/map_status
```

Тип карты:

```text
nav_msgs/msg/OccupancyGrid
```

Значения карты:

```text
0   — свободная клетка
100 — препятствие / граница / safety margin
```

Карта строится в плоскости Minecraft `X-Z`.

Соглашение координат:

```text
Minecraft X → ROS map X
Minecraft Z → ROS map Y
Minecraft Y → высота, в карте не используется
```

### 9.5. `path_planner_node`

Планировщик пути на основе алгоритма A*.

Читает:

```text
/drone/local_map
/drone/pose
/drone/goal
```

Публикует:

```text
/drone/planned_path
/drone/target
/drone/planner_status
```

Логика:

1. Получает текущую позицию дрона.
2. Получает high-level goal от mission planner.
3. Переводит start и goal в координаты grid-карты.
4. Запускает A*.
5. Публикует полный путь в `/drone/planned_path`.
6. Публикует ближайшую промежуточную цель в `/drone/target`.

### 9.6. `mission_planner_node`

Высокоуровневый планировщик миссии.

Публикует:

```text
/drone/goal
/drone/status
/drone/mission_state
```

Реализует state machine:

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

Mission planner не двигает дрон напрямую. Он задаёт только смысловые цели, а `path_planner_node` строит безопасный маршрут по карте.

### 9.7. `player_camera_follow_node`

Использует игрока как камеру-наблюдателя.

Подписывается на:

```text
/drone/pose
```

Через `/minecraft/command` телепортирует игрока рядом с Allay-дроном и направляет камеру в сторону дрона.

Публикует:

```text
/drone/camera_status
```

Параметры камеры задаются в `config/patrol_params.yaml`:

```yaml
offset_x: -8.0
offset_y: 8.0
offset_z: -8.0
```

### 9.8. `sensor_monitor_node`

Логирует сенсорные данные игрока:

```text
/player/ground_truth
/player/imu
```

Публикует:

```text
/drone/sensor_status
```

### 9.9. `visualizer_node`

Публикует RViz-маркеры:

```text
/drone/markers
/drone/visualizer_status
```

Визуализирует:

* текущую позицию дрона;
* текущую промежуточную цель;
* high-level goal миссии;
* waypoint-точки;
* inspection target;
* препятствия.

## 10. Основные ROS 2-топики

### Входные топики Minecraft

```text
/player/ground_truth
/player/imu
/player/image_raw
/player/pointcloud
/player/surrounding_block_array
```

В финальной версии проекта LiDAR/pointcloud не используется как обязательный компонент, потому что сенсоры `minecraft_ros2` относятся к игроку, а не к отдельной сущности Allay.

### Топики проекта

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

### Сервисы

```text
/minecraft/command
/spawn_entity
/dig_block
```

Основной сервис проекта:

```text
/minecraft/command
```

## 11. Сборка проекта

Перейти в workspace:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
```

Собрать:

```bash
colcon build
source install/setup.bash
```

Проверить исполняемые ноды:

```bash
ros2 pkg executables minecraft_drone_coursework
```

Ожидаемо должны быть ноды:

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

## 12. Запуск Minecraft

Minecraft нужно запускать из графического терминала Ubuntu, не через обычный SSH:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

Если в терминале отображается:

```text
92% EXECUTING
:runClient
```

это нормально. Gradle-задача `runClient` выполняется всё время, пока открыт Minecraft.

Далее в Minecraft:

```text
Singleplayer → выбрать Superflat-мир → Play Selected World
```

Если мира ещё нет, создать новый:

```text
Singleplayer → Create New World
Game Mode: Creative
Allow Cheats: ON
World Type: Superflat
Difficulty: Peaceful
```

## 13. Проверка связи Minecraft ↔ ROS 2

В отдельном терминале или через SSH:

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

## 14. Полный запуск курсового проекта

Убедиться, что Minecraft открыт и игрок находится внутри мира.

В графическом терминале Ubuntu или SSH-терминале:

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

1. В Minecraft создаётся испытательный полигон.
2. Появляется Allay-дрон с именем `ROS Drone`.
3. Дрон выполняет миссию.
4. Камера следует за дроном.
5. RViz2 показывает карту, препятствия, A* путь, фактическую траекторию, цель и позицию дрона.

## 15. Запуск по частям

### 15.1. Подготовить полигон

```bash
ros2 run minecraft_drone_coursework world_setup_node
```

### 15.2. Создать Allay-дрона

```bash
ros2 run minecraft_drone_coursework drone_spawn_node
```

### 15.3. Запустить карту

```bash
ros2 run minecraft_drone_coursework map_builder_node
```

Проверить:

```bash
ros2 topic echo --once /drone/map_status
```

### 15.4. Запустить контроллер дрона

```bash
ros2 run minecraft_drone_coursework drone_entity_controller_node
```

### 15.5. Запустить A* planner

```bash
ros2 run minecraft_drone_coursework path_planner_node
```

### 15.6. Отправить цель вручную

Например, inspection target:

```bash
ros2 topic pub --once /drone/goal geometry_msgs/msg/PoseStamped "{header: {frame_id: 'map'}, pose: {position: {x: 19.0, y: 19.0, z: 10.0}, orientation: {w: 1.0}}}"
```

Координаты:

```text
ROS x = Minecraft X
ROS y = Minecraft Z
ROS z = Minecraft Y / altitude
```

### 15.7. Запустить камеру

```bash
ros2 run minecraft_drone_coursework player_camera_follow_node
```

### 15.8. Запустить RViz-маркеры

```bash
ros2 run minecraft_drone_coursework visualizer_node
```

## 16. Мониторинг во время работы

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

Текущий A* путь:

```bash
ros2 topic echo --once /drone/planned_path
```

Текущая промежуточная цель:

```bash
ros2 topic echo /drone/target
```

Фактическая позиция дрона:

```bash
ros2 topic echo /drone/pose
```

Статус камеры:

```bash
ros2 topic echo /drone/camera_status
```

Карта:

```bash
ros2 topic echo --once /drone/local_map
```

## 17. RViz2

RViz2 запускается автоматически из `full_mission_astar.launch.py`.

Конфиг:

```text
rviz/minecraft_drone.rviz
```

Если RViz2 нужно открыть вручную:

```bash
rviz2 -d ~/minecraft_drone_ws/src/minecraft_drone_coursework/rviz/minecraft_drone.rviz
```

В RViz2 должны отображаться:

```text
/drone/local_map       — карта занятости
/drone/planned_path    — A* путь
/drone/path            — фактическая траектория
/drone/markers         — дрон, цели, waypoint-точки, препятствия
```

Если RViz пустой, проверить:

```text
Fixed Frame = map
```

И вручную добавить:

```text
Add → By topic → /drone/local_map → Map
Add → By topic → /drone/planned_path → Path
Add → By topic → /drone/path → Path
Add → By topic → /drone/markers → MarkerArray
```

## 18. Основной сценарий демонстрации

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

## 19. Запись rosbag

Для записи демонстрации:

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

Просмотр информации:

```bash
ros2 bag info <bag_folder>
```

## 20. Troubleshooting

### 20.1. Видны только `/rosout` и `/parameter_events`

Проблема: не подключён `ros2_java_ws` или Minecraft не запущен.

Проверить:

```bash
source ~/.bashrc
echo $ROS2JAVA_INSTALL_PATH
ros2 pkg list | grep minecraft_msgs
```

Ожидаемо:

```text
/home/nikita/ros2_java_ws/install
minecraft_msgs
```

Также проверить, что Minecraft открыт и игрок находится внутри мира:

```bash
ros2 topic list
```

### 20.2. `/minecraft/command` не найден

Проверить сервисы:

```bash
ros2 service list | grep minecraft
```

Если сервиса нет:

1. Убедиться, что Minecraft запущен через `./runClient.sh`.
2. Убедиться, что игрок внутри мира.
3. Перезапустить ROS daemon:

```bash
ros2 daemon stop
ros2 daemon start
```

### 20.3. Allay-дрон не виден

Возможные причины:

* `world_setup_node` удалил старого дрона;
* `drone_spawn_node` не был запущен;
* дрон далеко от камеры.

Решение:

```bash
ros2 run minecraft_drone_coursework world_setup_node
ros2 run minecraft_drone_coursework drone_spawn_node
```

Проверить телепортацией дрона перед игроком:

```bash
ros2 service call /minecraft/command minecraft_msgs/srv/Command "{command: 'execute as @p at @s run tp @e[tag=ros_drone,limit=1,sort=nearest] ^ ^1 ^5'}"
```

Подсветить:

```bash
ros2 service call /minecraft/command minecraft_msgs/srv/Command "{command: 'effect give @e[tag=ros_drone] minecraft:glowing 999999 1 true'}"
```

### 20.4. Игрок остался в spectator mode

Вернуть creative:

```bash
ros2 service call /minecraft/command minecraft_msgs/srv/Command "{command: 'gamemode creative @p'}"
```

### 20.5. Камера врезается в препятствия или плохо видит дрона

Поменять параметры в:

```text
config/patrol_params.yaml
```

Рекомендуемые значения:

```yaml
player_camera_follow_node:
  ros__parameters:
    offset_x: -8.0
    offset_y: 8.0
    offset_z: -8.0
```

После изменения:

```bash
cd ~/minecraft_drone_ws
colcon build
source install/setup.bash
```

### 20.6. A* пишет `PLANNING_FAILED`

Возможные причины:

* цель попала внутрь препятствия;
* safety margin слишком большой;
* препятствия перекрыли проход.

Уменьшить safety margin:

```yaml
map_builder_node:
  ros__parameters:
    safety_margin_cells: 1
```

После изменения:

```bash
cd ~/minecraft_drone_ws
colcon build
source install/setup.bash
```

### 20.7. RViz2 пустой

Проверить:

```text
Fixed Frame = map
```

Проверить топики:

```bash
ros2 topic list | grep drone
```

Проверить markers:

```bash
ros2 topic echo --once /drone/visualizer_status
```

## 21. Описание алгоритма A*

В проекте A* используется для поиска пути на 2D occupancy grid-карте.

Вход:

```text
start = текущая позиция дрона
goal = текущая цель миссии
map = /drone/local_map
```

Клетки карты:

```text
0   = свободно
100 = занято
```

Планировщик использует 8-связную сетку:

```text
вверх, вниз, влево, вправо, диагонали
```

Для диагоналей запрещено “срезание углов” рядом с препятствиями.

Эвристика:

```text
Euclidean distance
```

Результат:

```text
/drone/planned_path
```

Далее `path_planner_node` выбирает ближайшую промежуточную точку с lookahead distance и публикует её в:

```text
/drone/target
```

`drone_entity_controller_node` двигает Allay-дрона к этой точке.

## 22. Что реализовано в текущей версии

Реализовано:

* запуск Minecraft с ROS 2-модом;
* создание полигона через ROS 2 service;
* отдельный Allay-дрон;
* high-level mission planner;
* 2D occupancy grid;
* A* path planning;
* движение дрона по planned path;
* камера, следующая за дроном;
* RViz2-визуализация;
* markers для дрона, целей и препятствий;
* мониторинг ROS 2-топиков;
* launch-файл для полного запуска.

## 23. Ограничения текущей версии

* Физика дрона не моделируется.
* Allay перемещается через команды Minecraft `tp`, а не через динамическую модель.
* Карта строится по заранее известным препятствиям, а не по LiDAR/SLAM.
* Сенсоры `minecraft_ros2` относятся к игроку, а не к Allay-сущности.
* Полноценный SLAM/Nav2 не используется.
* Препятствия считаются 2D no-fly зонами на карте.

## 24. Возможные улучшения

* Добавить выбор миссии через YAML.
* Добавить dynamic reconfigure параметров скорости.
* Добавить кнопку emergency stop.
* Добавить ручную постановку цели через RViz2.
* Реализовать обход новых динамических препятствий.
* Использовать `/player/surrounding_block_array` для построения карты.
* Добавить запись и анализ rosbag.
* Добавить генерацию отчёта по пройденной траектории.
* Добавить сравнение прямого маршрута и A* маршрута.
* Добавить метрики:

  * длина пути;
  * время выполнения миссии;
  * число перепланирований;
  * минимальное расстояние до препятствий.

## 25. Команды быстрого запуска

### Запуск Minecraft

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

### Запуск проекта

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
ros2 launch minecraft_drone_coursework full_mission_astar.launch.py
```

### Мониторинг миссии

```bash
ros2 topic echo /drone/mission_state
```

### Мониторинг A*

```bash
ros2 topic echo /drone/planner_status
```

### Вернуть игрока в creative

```bash
ros2 service call /minecraft/command minecraft_msgs/srv/Command "{command: 'gamemode creative @p'}"
```

### Создать backup workspace

```bash
cd ~
tar -czf minecraft_drone_ws_working_backup.tar.gz minecraft_drone_ws
```

### Создать backup Minecraft-миров и мода

```bash
cd ~
tar -czf minecraft_ros2_working_backup.tar.gz minecraft_ros2
```

## 26. Краткая формулировка для отчёта

В рамках проекта разработана ROS 2-система автономного патрулирования виртуального дрона в Minecraft-среде. В качестве виртуального дрона используется отдельная Minecraft-сущность `Allay`, управляемая через сервис `/minecraft/command`. Система включает автоматическую подготовку испытательного полигона, построение 2D-карты занятости, планирование маршрута с помощью алгоритма A*, выполнение миссии по состояниям и визуализацию в RViz2. Minecraft используется как учебная 3D-среда-симулятор, а RViz2 — как инструмент робототехнической визуализации карты, маршрута и состояния дрона.
