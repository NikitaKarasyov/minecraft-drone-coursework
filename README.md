# ROS 2 Minecraft Drone Patrol

Курсовой проект по дисциплине **«Основы мобильной робототехники»**.

Проект реализует ROS 2-систему автономного патрулирования виртуального дрона в Minecraft-среде. В качестве дрона используется отдельная Minecraft-сущность `Allay`, управляемая из ROS 2 через сервис `/minecraft/command`.

Minecraft используется как трёхмерная среда симуляции, `minecraft_ros2` обеспечивает двустороннее взаимодействие игрового мира с ROS 2, а RViz2 применяется для инженерной визуализации карты, маршрута, целей и фактической траектории дрона.

## 1. Цель проекта

Цель работы — разработать учебную робототехническую систему, которая демонстрирует:

* интеграцию Minecraft Java Edition с ROS 2;
* создание виртуального испытательного полигона;
* управление отдельным объектом-дроном из ROS 2;
* построение двумерной карты занятости;
* планирование маршрута с помощью алгоритма A*;
* выполнение миссии на основе конечного автомата;
* визуализацию карты, маршрута и траектории в RViz2.

## 2. Итоговая демонстрация

В демонстрации система выполняет следующий сценарий:

1. Minecraft запускается с модом `minecraft_ros2`.
2. Мод подключает Minecraft к ROS 2 и регистрирует игровые топики и сервисы.
3. ROS 2 создаёт испытательный полигон: платформу, препятствия, waypoint-зоны и цель инспекции.
4. ROS 2 создаёт отдельного Allay-дрона.
5. `map_builder_node` строит 2D occupancy grid-карту.
6. `mission_planner_node` задаёт высокоуровневые цели миссии.
7. `path_planner_node` строит A*-маршрут до текущей цели.
8. `drone_entity_controller_node` перемещает Allay-дрона по маршруту.
9. `player_camera_follow_node` ведёт игрока-камеру за дроном.
10. RViz2 показывает карту, препятствия, A*-путь, фактическую траекторию, цель и положение дрона.

## 3. Архитектура

```text
Minecraft Java Edition
  └── Forge + minecraft_ros2
        ├── публикует данные Minecraft в ROS 2
        ├── принимает команды управления игроком
        └── предоставляет сервис /minecraft/command
                         │
                         │ ROS 2 topics и services
                         ▼
                ROS 2 Humble middleware
                         │
          ┌──────────────┴───────────────┐
          ▼                              ▼
Python-ноды проекта                  RViz2
```

Архитектура прикладной части проекта:

```text
world_setup_node
  создаёт Minecraft-полигон, препятствия, цель и waypoint-зоны
  вызывает /minecraft/command

drone_spawn_node
  создаёт отдельную Minecraft-сущность Allay с тегом ros_drone
  вызывает /minecraft/command

map_builder_node
  строит 2D occupancy grid-карту известных препятствий
  публикует /drone/local_map

mission_planner_node
  реализует state machine:
  TAKEOFF → PATROL_REDSTONE → PATROL_EMERALD → PATROL_LAPIS
  → GO_TO_INSPECTION → INSPECT → RETURN_HOME → LAND → DONE
  публикует высокоуровневую цель в /drone/goal

path_planner_node
  читает /drone/local_map, /drone/pose и /drone/goal
  строит A*-маршрут
  публикует /drone/planned_path и промежуточную /drone/target

drone_entity_controller_node
  читает /drone/target
  вычисляет очередное положение дрона
  перемещает Allay через /minecraft/command
  публикует /drone/pose и /drone/path

player_camera_follow_node
  читает /drone/pose
  перемещает игрока-камеру через /minecraft/command

visualizer_node
  публикует RViz-маркеры в /drone/markers

RViz2
  показывает карту, препятствия, путь, траекторию, цель и положение дрона
```

## 4. Используемые технологии

* Ubuntu 22.04;
* ROS 2 Humble;
* Python 3.10;
* Minecraft Java Edition;
* Minecraft Forge;
* `minecraft_ros2`;
* `ros2_java`;
* `rcljava`;
* Java 21;
* RViz2;
* ROS 2 topics, services и launch-файлы;
* `nav_msgs/msg/OccupancyGrid`;
* `nav_msgs/msg/Path`;
* `geometry_msgs/msg/PoseStamped`;
* `visualization_msgs/msg/MarkerArray`;
* `minecraft_msgs/srv/Command`.

## 5. Взаимодействие ROS 2 и Minecraft через minecraft_ros2

### 5.1. Назначение minecraft_ros2

`minecraft_ros2` — это мод для Minecraft Java Edition, который подключает игровой процесс к ROS 2.

После запуска Minecraft с модом внутри Java-процесса создаются ROS 2-компоненты, которые:

* публикуют состояние игрока и игрового окружения;
* публикуют данные виртуальных сенсоров;
* принимают команды управления игроком;
* предоставляют ROS 2-сервисы для изменения игрового мира;
* позволяют другим ROS 2-нодам взаимодействовать с Minecraft стандартными средствами ROS 2.

В результате Minecraft становится участником ROS 2-графа наравне с Python-нодами проекта.

Прикладные Python-ноды не обращаются к внутреннему Java API Minecraft напрямую. Они используют стандартные ROS 2-интерфейсы: топики, сервисы и сообщения.

### 5.2. Программные уровни интеграции

В проекте используются три основных уровня:

```text
Minecraft Java Edition
        │
        │ внутренний Minecraft/Forge API
        ▼
minecraft_ros2
        │
        │ ros2_java / rcljava
        ▼
ROS 2 middleware
        │
        │ topics и services
        ▼
Python-ноды minecraft_drone_coursework
```

#### Minecraft Java Edition

Minecraft содержит игровой мир, блоки, игрока и сущности. В нашем проекте отдельная сущность `Allay` используется как видимый виртуальный дрон.

#### minecraft_ros2

Мод связывает события и объекты Minecraft с ROS 2-интерфейсами. Например:

* положение игрока преобразуется в ROS-сообщение;
* изображение игровой камеры публикуется как `sensor_msgs/msg/Image`;
* Minecraft-команда, полученная через ROS 2 service, выполняется внутри мира;
* сообщение `geometry_msgs/msg/Twist` может использоваться для управления игроком.

#### ros2_java и rcljava

Minecraft работает на Java, поэтому для создания ROS 2 publishers, subscribers и services внутри мода используется Java-клиент ROS 2.

`ros2_java` предоставляет Java-привязки ROS 2, а `rcljava` позволяет Java-коду регистрировать ноды, топики, клиентов и сервисы в общем ROS 2-графе.

#### Python-ноды проекта

Ноды пакета `minecraft_drone_coursework` реализованы на Python с использованием `rclpy`. Они находятся в отдельных процессах, но взаимодействуют с Java-модом через ROS 2 middleware.

Таким образом, Python- и Java-компоненты не требуют прямого вызова функций друг друга.

### 5.3. Двунаправленный обмен

Связь работает в двух направлениях.

#### Minecraft → ROS 2

Minecraft публикует информацию о состоянии игрового мира:

```text
Minecraft
  → minecraft_ros2
  → ROS 2 publisher
  → ROS 2 topic
  → Python subscriber / диагностические команды
```

Примеры данных:

* положение игрока;
* IMU;
* изображение игровой камеры;
* облако точек;
* блоки вокруг игрока;
* трансформации координат.

#### ROS 2 → Minecraft

ROS 2 передаёт команды управления в игровой мир:

```text
Python ROS 2 node
  → ROS 2 client или publisher
  → minecraft_ros2
  → Minecraft command / player control
  → изменение игрового мира
```

В нашей курсовой основной канал ROS 2 → Minecraft — сервис:

```text
/minecraft/command
```

### 5.4. Интерфейсы, публикуемые minecraft_ros2

После запуска Minecraft и входа в мир в ROS 2-графе доступны следующие основные топики.

| Топик                             | Тип                             | Назначение                             |
| --------------------------------- | ------------------------------- | -------------------------------------- |
| `/player/ground_truth`            | `geometry_msgs/msg/Pose`        | Истинное положение и ориентация игрока |
| `/player/image_raw`               | `sensor_msgs/msg/Image`         | Изображение игровой камеры             |
| `/player/imu`                     | `sensor_msgs/msg/Imu`           | Виртуальные инерциальные данные        |
| `/player/pointcloud`              | `sensor_msgs/msg/PointCloud2`   | Облако точек виртуального LiDAR        |
| `/player/surrounding_block_array` | `minecraft_msgs/msg/BlockArray` | Информация о блоках вокруг игрока      |
| `/tf`                             | `tf2_msgs/msg/TFMessage`        | Трансформации систем координат         |

Проверить фактические типы интерфейсов в установленной версии можно командами:

```bash
ros2 topic info /player/ground_truth
ros2 topic info /player/image_raw
ros2 topic info /player/imu
ros2 topic info /player/pointcloud
ros2 topic info /player/surrounding_block_array
```

### 5.5. Виртуальные сенсоры

#### Положение игрока

Топик:

```text
/player/ground_truth
```

содержит истинную позицию и ориентацию игрока в Minecraft.

Пример просмотра:

```bash
ros2 topic echo --once /player/ground_truth
```

Данные ground truth удобны для:

* проверки связи Minecraft с ROS 2;
* отладки координат;
* проверки перемещения игрока;
* сравнения с виртуальными сенсорными измерениями.

В текущем проекте положение самого Allay-дрона публикуется отдельно нашей нодой в `/drone/pose`, поскольку `minecraft_ros2` предоставляет стандартные сенсоры прежде всего для игрока.

#### IMU

Топик:

```text
/player/imu
```

публикует данные типа:

```text
sensor_msgs/msg/Imu
```

Проверка:

```bash
ros2 topic hz /player/imu
ros2 topic echo --once /player/imu
```

В нашей системе IMU используется только для диагностики через `sensor_monitor_node` и не участвует в A*-планировании.

#### Камера

Топик:

```text
/player/image_raw
```

передаёт изображение из игровой камеры в стандартном формате ROS 2:

```text
sensor_msgs/msg/Image
```

Это позволяет в дальнейшем подключить:

* OpenCV;
* распознавание объектов;
* визуальную навигацию;
* запись изображений в rosbag;
* отображение изображения в RViz2.

В текущей версии изображение не используется для построения маршрута.

#### LiDAR

Топик:

```text
/player/pointcloud
```

использует тип:

```text
sensor_msgs/msg/PointCloud2
```

В стандартной логике `minecraft_ros2` публикация облака точек связана с виртуальным LiDAR-сенсором игрока.

В текущей версии курсовой LiDAR не используется. Причина состоит в том, что видимым дроном является отдельная сущность `Allay`, тогда как стандартные сенсоры `minecraft_ros2` привязаны к игроку.

Вместо сенсорного картирования используется карта заранее известного полигона.

#### Информация о блоках

Топик:

```text
/player/surrounding_block_array
```

передаёт информацию о блоках вокруг игрока.

В будущей версии этот интерфейс может использоваться для:

* построения карты по наблюдаемым блокам;
* обнаружения ранее неизвестных препятствий;
* локального перепланирования;
* замены заранее заданной карты на карту, формируемую во время миссии.

### 5.6. Управление игроком через /cmd_vel

`minecraft_ros2` предоставляет стандартный ROS 2-топик:

```text
/cmd_vel
```

Тип сообщения:

```text
geometry_msgs/msg/Twist
```

Пример команды:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 1.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Этот интерфейс управляет игроком Minecraft.

В нашем проекте `/cmd_vel` не применяется для управления дроном, потому что дроном является не игрок, а отдельная сущность `Allay`.

Поэтому управление разделено:

```text
/player/... и /cmd_vel
  относятся к игроку Minecraft

/drone/... и /minecraft/command
  используются для логики отдельного Allay-дрона
```

Игрок в проекте выполняет роль камеры-наблюдателя.

### 5.7. Сервисы minecraft_ros2

После запуска Minecraft доступны сервисы:

```text
/minecraft/command
/spawn_entity
/dig_block
```

В текущей реализации курсовой непосредственно используется сервис:

```text
/minecraft/command
```

Остальные сервисы предоставляет `minecraft_ros2`, но основная логика проекта построена на выполнении обычных команд Minecraft через универсальный сервис `Command`.

### 5.8. Сервис /minecraft/command

Тип сервиса:

```text
minecraft_msgs/srv/Command
```

Структура запроса и ответа:

```text
Request:
  string command

Response:
  bool success
  string message
```

Запрос содержит Minecraft-команду без начального символа `/`.

Пример:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'time set day'}"
```

Ожидаемый ответ:

```text
success: true
message: Success
```

Общая последовательность вызова:

```text
Python-нода
  создаёт Command.Request
        │
        ▼
ROS 2 service client
        │
        ▼
/minecraft/command
        │
        ▼
minecraft_ros2 принимает строку
        │
        ▼
Minecraft выполняет команду
        │
        ▼
minecraft_ros2 возвращает success и message
```

Сервис выполняет команду в мире, в котором находится игрок. Поэтому Minecraft должен быть запущен, а игрок должен находиться внутри загруженного мира.

### 5.9. Использование minecraft_ros2 в нодах проекта

#### world_setup_node

`world_setup_node` создаёт клиента:

```text
/minecraft/command
```

и последовательно выполняет команды Minecraft.

Основные команды:

```text
time set day
weather clear
difficulty peaceful
gamerule doMobSpawning false
gamerule doDaylightCycle false
gamerule doWeatherCycle false
fill ...
setblock ...
kill ...
tp ...
gamemode ...
```

За счёт этого полигон полностью воспроизводится автоматически.

Поток данных:

```text
world_setup_node
  → Command.Request
  → /minecraft/command
  → minecraft_ros2
  → Minecraft world
```

#### drone_spawn_node

`drone_spawn_node` создаёт отдельного Allay-дрона командой `summon`.

Упрощённый пример:

```text
summon minecraft:allay 0 8 0
```

Дополнительные NBT-параметры задают:

* тег `ros_drone`;
* имя `ROS Drone`;
* отключённый AI;
* отключённую гравитацию;
* неуязвимость;
* постоянное существование;
* визуальную подсветку.

После этого другие ноды обращаются к дрону через selector:

```text
@e[tag=ros_drone,limit=1]
```

#### drone_entity_controller_node

Контроллер получает очередную цель из:

```text
/drone/target
```

Затем он:

1. вычисляет расстояние до цели;
2. определяет направление движения;
3. рассчитывает очередной небольшой шаг;
4. формирует команду `tp`;
5. вызывает `/minecraft/command`;
6. публикует новую расчётную позицию в `/drone/pose`.

Пример формируемой команды:

```text
tp @e[tag=ros_drone,limit=1,sort=nearest] 8.250 10.000 4.500
```

Полный поток:

```text
path_planner_node
  → /drone/target
  → drone_entity_controller_node
  → /minecraft/command
  → minecraft_ros2
  → телепортация Allay в Minecraft
```

#### player_camera_follow_node

Нода читает:

```text
/drone/pose
```

и вычисляет положение игрока со смещением относительно Allay.

Далее через `/minecraft/command` выполняются команды:

```text
gamemode spectator @p
tp @p x y z yaw pitch
```

Таким образом игрок автоматически следует за дроном и смотрит в его сторону.

Игрок используется только как демонстрационная камера, а не как управляемый дрон.

### 5.10. Интерфейсы нашего проекта и интерфейсы minecraft_ros2

Важно различать две группы интерфейсов.

#### Интерфейсы minecraft_ros2

Они создаются Minecraft-модом:

```text
/player/ground_truth
/player/image_raw
/player/imu
/player/pointcloud
/player/surrounding_block_array
/cmd_vel
/minecraft/command
/spawn_entity
/dig_block
/tf
```

#### Интерфейсы minecraft_drone_coursework

Они создаются Python-нодами нашей курсовой:

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

`minecraft_ros2` отвечает за связь с игровым миром, а пакет `minecraft_drone_coursework` реализует прикладную логику миссии.

### 5.11. Система координат

Minecraft использует координаты:

```text
X — горизонтальная ось
Y — высота
Z — горизонтальная ось
```

Для карты и RViz2 в проекте используется соглашение:

```text
ROS x = Minecraft X
ROS y = Minecraft Z
ROS z = Minecraft Y
```

То есть горизонтальная плоскость Minecraft `X-Z` отображается в горизонтальную плоскость ROS `x-y`, а высота Minecraft `Y` становится координатой ROS `z`.

Пример:

```text
Minecraft:
X = 10
Y = 8
Z = 4

ROS:
x = 10
y = 4
z = 8
```

Преобразование используется в:

* `mission_planner_node`;
* `path_planner_node`;
* `drone_entity_controller_node`;
* `player_camera_follow_node`;
* `visualizer_node`.

### 5.12. Пользовательские сообщения minecraft_msgs

Для специальных Minecraft-интерфейсов применяется пакет:

```text
minecraft_msgs
```

Он содержит определения сообщений и сервисов, которых нет в стандартных пакетах ROS 2.

В проекте непосредственно используется:

```text
minecraft_msgs/srv/Command
```

Кроме того, в ROS 2-графе используется:

```text
minecraft_msgs/msg/BlockArray
```

Проверить доступность интерфейсов:

```bash
ros2 pkg list | grep minecraft_msgs
ros2 interface show minecraft_msgs/srv/Command
ros2 interface show minecraft_msgs/msg/BlockArray
```

Поскольку Minecraft-мод написан на Java, для него генерируются Java-классы ROS-сообщений. Python-ноды используют те же определения интерфейсов через `rclpy`.

Это позволяет Java- и Python-компонентам корректно обмениваться типизированными сообщениями.

### 5.13. Настройка общей ROS 2-среды

Minecraft-мод и Python-ноды должны использовать одну ROS 2-среду.

В `~/.bashrc` подключаются:

```bash
source /opt/ros/humble/setup.bash

export ROS2JAVA_INSTALL_PATH=$HOME/ros2_java_ws/install
source $ROS2JAVA_INSTALL_PATH/setup.bash

export ROS_DOMAIN_ID=0

source ~/minecraft_drone_ws/install/setup.bash
```

Здесь:

* `/opt/ros/humble/setup.bash` подключает ROS 2 Humble;
* `ros2_java_ws/install/setup.bash` подключает Java-клиент и `minecraft_msgs`;
* `ROS_DOMAIN_ID=0` помещает все компоненты в один ROS 2 domain;
* `minecraft_drone_ws/install/setup.bash` подключает Python-пакет курсовой.

Если компоненты используют разные `ROS_DOMAIN_ID`, они не увидят топики и сервисы друг друга.

### 5.14. Полный пример взаимодействия

Рассмотрим перемещение дрона к очередной точке маршрута.

```text
1. mission_planner_node публикует /drone/goal.

2. path_planner_node:
   - читает /drone/goal;
   - читает /drone/local_map;
   - читает /drone/pose;
   - строит A*-маршрут;
   - публикует /drone/planned_path;
   - выбирает промежуточную точку;
   - публикует /drone/target.

3. drone_entity_controller_node:
   - читает /drone/target;
   - рассчитывает очередную позицию;
   - создаёт запрос minecraft_msgs/srv/Command;
   - отправляет команду tp в /minecraft/command.

4. minecraft_ros2:
   - принимает сервисный запрос;
   - выполняет команду внутри Minecraft;
   - возвращает результат выполнения.

5. Minecraft:
   - перемещает Allay;
   - отображает новое положение сущности.

6. drone_entity_controller_node:
   - публикует новую расчётную позицию в /drone/pose;
   - добавляет её в /drone/path.

7. RViz2:
   - получает /drone/pose;
   - получает /drone/path;
   - получает /drone/planned_path;
   - отображает положение и маршруты.
```

Таким образом, `minecraft_ros2` является связующим слоем между алгоритмами навигации ROS 2 и объектами игрового мира Minecraft.

## 6. Рабочие директории

```text
~/ros2_java_ws
~/minecraft_ros2
~/minecraft_drone_ws
```

Назначение директорий:

```text
~/ros2_java_ws
  ros2_java, rcljava и Java-интерфейсы ROS 2

~/minecraft_ros2
  исходный код и среда запуска Minecraft-мода

~/minecraft_drone_ws
  Python-ноды курсового проекта
```

Пакет курсового проекта:

```text
~/minecraft_drone_ws/src/minecraft_drone_coursework
```

## 7. Структура пакета

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

## 8. Подготовка окружения

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

Проверка `ros2_java`, `rcljava` и сообщений Minecraft:

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

## 9. Сборка проекта

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

## 10. Запуск Minecraft

Minecraft запускается из графического терминала Ubuntu:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

`runClient.sh` запускает Gradle-задачу Forge development client с подключённым модом `minecraft_ros2`.

После появления главного меню необходимо зайти в мир Minecraft. Для проекта используется `Superflat`-мир в режиме `Creative` с включёнными cheats.

ROS 2-интерфейсы, зависящие от игрового мира и игрока, становятся доступны после загрузки мира.

## 11. Проверка связи Minecraft ↔ ROS 2

В отдельном терминале:

```bash
source ~/.bashrc
ros2 node list
ros2 topic list
ros2 service list
```

Ожидаемые топики `minecraft_ros2`:

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

Проверка типа сервиса:

```bash
ros2 service type /minecraft/command
ros2 interface show minecraft_msgs/srv/Command
```

Проверка команды Minecraft:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'time set day'}"
```

Ожидаемый ответ:

```text
success: true
message: Success
```

Проверка данных Minecraft:

```bash
ros2 topic echo --once /player/ground_truth
ros2 topic echo --once /player/imu
```

## 12. Полный запуск проекта

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
* RViz2 показывает карту, препятствия, A*-путь, фактическую траекторию, цель и позицию дрона.

## 13. Запуск по частям

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

Запустить A*-планировщик:

```bash
ros2 run minecraft_drone_coursework path_planner_node
```

Отправить цель вручную:

```bash
ros2 topic pub --once \
  /drone/goal \
  geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'map'}, pose: {position: {x: 19.0, y: 19.0, z: 10.0}, orientation: {w: 1.0}}}"
```

Запустить камеру:

```bash
ros2 run minecraft_drone_coursework player_camera_follow_node
```

Запустить RViz-маркеры:

```bash
ros2 run minecraft_drone_coursework visualizer_node
```

## 14. Основные топики проекта

| Топик                      | Назначение                             |
| -------------------------- | -------------------------------------- |
| `/drone/pose`              | Текущая расчётная позиция Allay-дрона  |
| `/drone/path`              | Фактическая траектория движения        |
| `/drone/target`            | Текущая промежуточная цель контроллера |
| `/drone/goal`              | Высокоуровневая цель миссии            |
| `/drone/local_map`         | Двумерная карта занятости              |
| `/drone/planned_path`      | Путь, построенный алгоритмом A*        |
| `/drone/status`            | Текстовый статус миссии                |
| `/drone/mission_state`     | Текущее состояние конечного автомата   |
| `/drone/controller_status` | Статус контроллера движения            |
| `/drone/planner_status`    | Статус A*-планировщика                 |
| `/drone/map_status`        | Статус построителя карты               |
| `/drone/camera_status`     | Статус камеры сопровождения            |
| `/drone/sensor_status`     | Диагностический статус сенсоров        |
| `/drone/visualizer_status` | Статус визуализатора                   |
| `/drone/markers`           | Маркеры для RViz2                      |

## 15. Основной сервис проекта

Основным интерфейсом связи прикладных нод с Minecraft является:

```text
/minecraft/command
```

Он используется для:

* подготовки мира;
* создания дрона;
* перемещения Allay;
* перемещения игрока-камеры;
* настройки режима игры;
* изменения времени и погоды.

## 16. Mission state machine

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

Mission planner не управляет дроном напрямую.

Он публикует смысловую цель в:

```text
/drone/goal
```

После этого `path_planner_node` строит A*-маршрут и публикует промежуточную цель в:

```text
/drone/target
```

## 17. Алгоритм A*

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

Вокруг препятствий добавляется safety margin:

```text
safety_margin_cells: 2
```

При разрешении карты `1.0` одна клетка соответствует одному блоку Minecraft, поэтому безопасный запас составляет приблизительно два блока.

Планировщик использует 8-связную сетку:

* четыре ортогональных перехода;
* четыре диагональных перехода.

Стоимость ортогонального шага:

```text
1
```

Стоимость диагонального шага:

```text
sqrt(2)
```

Для клетки `n` вычисляется:

```text
f(n) = g(n) + h(n)
```

где:

* `g(n)` — стоимость пути от старта до клетки;
* `h(n)` — евклидова оценка расстояния до цели;
* `f(n)` — оценка полной стоимости пути через клетку.

На каждой итерации выбирается клетка с минимальным значением `f(n)`.

Для диагональных переходов запрещено срезание углов рядом с препятствиями.

## 18. RViz2

RViz2 запускается автоматически из `full_mission_astar.launch.py`.

Конфигурация:

```text
rviz/minecraft_drone.rviz
```

В RViz2 отображаются:

```text
/drone/local_map       — карта занятости
/drone/planned_path    — A*-путь
/drone/path            — фактическая траектория
/drone/markers         — дрон, цели, waypoint-точки и препятствия
```

Если RViz2 запускается вручную:

```bash
rviz2 -d \
~/minecraft_drone_ws/src/minecraft_drone_coursework/rviz/minecraft_drone.rviz
```

## 19. Мониторинг

Состояние миссии:

```bash
ros2 topic echo /drone/mission_state
```

Статус mission planner:

```bash
ros2 topic echo /drone/status
```

Статус A*-планировщика:

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

Проверка связи с Minecraft:

```bash
ros2 topic echo --once /player/ground_truth
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'time set day'}"
```

## 20. Запись rosbag

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

## 21. Сценарий демонстрации

1. Запустить Minecraft:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

2. Зайти в Superflat-мир.

3. Проверить интерфейсы `minecraft_ros2`:

```bash
ros2 topic list
ros2 service list
```

4. Запустить проект:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
ros2 launch minecraft_drone_coursework full_mission_astar.launch.py
```

5. Показать в Minecraft:

   * автоматически созданный полигон;
   * препятствия;
   * Allay-дрона;
   * обход препятствий;
   * камеру, следующую за дроном.

6. Показать в RViz2:

   * occupancy grid;
   * planned path;
   * actual path;
   * current goal;
   * current target;
   * положение дрона.

7. Показать терминалы мониторинга:

```bash
ros2 topic echo /drone/mission_state
ros2 topic echo /drone/planner_status
```

8. Продемонстрировать прямое управление Minecraft через ROS 2:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'time set night'}"
```

Затем:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'time set day'}"
```

## 22. Ограничения

* Физика дрона не моделируется.
* Allay перемещается через команды Minecraft `tp`.
* Карта строится по заранее известным препятствиям.
* Полноценный SLAM и Nav2 не используются.
* Препятствия считаются двумерными no-fly зонами.
* Сенсоры `minecraft_ros2` относятся к игроку, а не к Allay-сущности.
* `/drone/pose` является расчётной позицией контроллера, а не независимым измерением положения сущности.
* Динамические изменения Minecraft-мира автоматически не переносятся в карту занятости.

## 23. Возможные улучшения

* Выбор миссии через YAML.
* Ручная постановка цели через RViz2.
* Emergency stop.
* Запись и анализ rosbag.
* Построение карты по `/player/surrounding_block_array`.
* Использование `/player/pointcloud` для сенсорного картирования.
* Добавление динамических препятствий.
* Сравнение прямого маршрута и A*-маршрута.
* Метрики длины пути, времени миссии и числа перепланирований.
* Независимое считывание фактической позиции Allay из Minecraft.
* Добавление компьютерного зрения на основе `/player/image_raw`.

## 24. Быстрые команды

Запуск Minecraft:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

Проверка интерфейсов Minecraft:

```bash
ros2 topic list
ros2 service list
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

Команда Minecraft из ROS 2:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'time set day'}"
```

Вернуть игрока в creative:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'gamemode creative @p'}"
```
