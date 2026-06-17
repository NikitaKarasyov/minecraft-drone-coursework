# CLAUDE.md

## Назначение этого файла

Этот файл является рабочей инструкцией для Claude Code при разработке, запуске, тестировании и расширении проекта `minecraft_drone_coursework`.

Claude должен использовать его как основной контекст репозитория, но перед любыми изменениями обязан сверять инструкции с фактическим состоянием кода. Если структура репозитория изменилась, приоритет имеет реальный код, а `CLAUDE.md` и `README.md` должны быть обновлены вместе с изменениями.

Главная задача Claude в этом проекте:

- поддерживать работоспособную интеграцию ROS 2 и Minecraft;
- уметь собрать и запустить проект;
- безопасно настраивать карту, препятствия, waypoint-точки и миссию;
- сохранять разделение между планированием миссии, A*-планированием и управлением дроном;
- добавлять пользовательские функции через новые ROS 2-ноды, топики, сервисы и параметры;
- не ломать внешние зависимости `minecraft_ros2` и `ros2_java`;
- не выполнять разрушительные действия без явного согласия пользователя.

---

## 1. Назначение проекта

`ROS 2 Minecraft Drone Patrol` — учебный проект по мобильной робототехнике.

Проект реализует автономное патрулирование виртуального дрона в Minecraft:

1. Minecraft запускается с модом `minecraft_ros2`.
2. ROS 2 через `/minecraft/command` создаёт полигон.
3. В качестве дрона создаётся отдельная сущность `minecraft:allay`.
4. Строится известная двумерная occupancy grid-карта.
5. `mission_planner_node` задаёт последовательность целей.
6. `path_planner_node` строит маршрут алгоритмом A*.
7. `drone_entity_controller_node` перемещает Allay к промежуточным точкам.
8. `player_camera_follow_node` использует игрока только как камеру-наблюдателя.
9. RViz2 показывает карту, планируемый путь, фактическую траекторию, цели и состояние миссии.

Minecraft в проекте является трёхмерной визуальной средой, а ROS 2 отвечает за архитектуру управления, планирование и обмен данными.

---

## 2. Границы репозитория и внешние зависимости

Основной репозиторий проекта:

```text
~/minecraft_drone_ws/src/minecraft_drone_coursework
```

Workspace проекта:

```text
~/minecraft_drone_ws
```

Внешние зависимости расположены отдельно:

```text
~/minecraft_ros2
~/ros2_java_ws
```

Их назначение:

```text
~/minecraft_ros2
  Minecraft Forge-мод, связывающий Minecraft с ROS 2

~/ros2_java_ws
  ros2_java, rcljava и minecraft_msgs

~/minecraft_drone_ws
  Python-ноды, launch-файлы, конфигурация и RViz проекта
```

Claude не должен считать `minecraft_ros2` и `ros2_java_ws` частью текущего репозитория, даже если они находятся на той же машине.

---

## 3. Используемые технологии

Основная среда:

- Ubuntu 22.04;
- ROS 2 Humble;
- Python 3.10;
- `rclpy`;
- Java 21;
- Minecraft Java Edition;
- Minecraft Forge;
- `minecraft_ros2`;
- `ros2_java`;
- `rcljava`;
- RViz2;
- DDS middleware ROS 2;
- Git и GitHub.

Основные ROS 2-интерфейсы:

- `geometry_msgs/msg/Pose`;
- `geometry_msgs/msg/PoseStamped`;
- `geometry_msgs/msg/Twist`;
- `nav_msgs/msg/OccupancyGrid`;
- `nav_msgs/msg/Path`;
- `sensor_msgs/msg/Image`;
- `sensor_msgs/msg/Imu`;
- `sensor_msgs/msg/PointCloud2`;
- `std_msgs/msg/String`;
- `visualization_msgs/msg/MarkerArray`;
- `minecraft_msgs/srv/Command`.

---

## 4. Структура проекта

Ожидаемая структура пакета:

```text
minecraft_drone_coursework/
├── CLAUDE.md
├── README.md
├── package.xml
├── setup.py
├── setup.cfg
├── resource/
│   └── minecraft_drone_coursework
├── minecraft_drone_coursework/
│   ├── __init__.py
│   ├── world_setup_node.py
│   ├── drone_spawn_node.py
│   ├── drone_entity_controller_node.py
│   ├── mission_planner_node.py
│   ├── map_builder_node.py
│   ├── path_planner_node.py
│   ├── player_camera_follow_node.py
│   ├── sensor_monitor_node.py
│   └── visualizer_node.py
├── launch/
│   ├── full_mission_astar.launch.py
│   ├── astar_planner_test.launch.py
│   ├── map_builder.launch.py
│   └── spawn_drone.launch.py
├── config/
│   └── patrol_params.yaml
└── rviz/
    └── minecraft_drone.rviz
```

Если фактическая структура отличается, Claude должен сначала вывести:

```bash
pwd
find . -maxdepth 3 -type f | sort
git status --short
```

и только после этого планировать изменения.

---

## 5. Архитектура системы

### 5.1. Общий поток данных

```text
Minecraft Java Edition
        │
        ▼
minecraft_ros2
        │ topics / services
        ▼
ROS 2 middleware
        │
        ├── world_setup_node
        ├── drone_spawn_node
        ├── map_builder_node
        ├── mission_planner_node
        ├── path_planner_node
        ├── drone_entity_controller_node
        ├── player_camera_follow_node
        ├── sensor_monitor_node
        └── visualizer_node
        │
        ▼
RViz2
```

### 5.2. Поток управления дроном

```text
mission_planner_node
  публикует /drone/goal
        │
        ▼
path_planner_node
  строит A*
  публикует /drone/planned_path
  публикует /drone/target
        │
        ▼
drone_entity_controller_node
  вычисляет очередной шаг
  вызывает /minecraft/command
        │
        ▼
minecraft_ros2
        │
        ▼
Allay перемещается в Minecraft
```

### 5.3. Ответственность нод

#### `world_setup_node`

Отвечает только за подготовку мира:

- платформа;
- стены и препятствия;
- стартовая зона;
- waypoint-зоны;
- inspection-зона;
- время, погода и gamerules;
- удаление старой сущности с тегом `ros_drone`.

Не должен содержать A*, mission state machine или управление движением.

#### `drone_spawn_node`

Создаёт отдельную сущность:

```text
minecraft:allay
```

С обязательным тегом:

```text
ros_drone
```

Обычно задаются:

- `NoAI`;
- `NoGravity`;
- `Invulnerable`;
- `PersistenceRequired`;
- `Glowing`;
- `CustomName`.

#### `map_builder_node`

Публикует:

```text
/drone/local_map
```

Тип:

```text
nav_msgs/msg/OccupancyGrid
```

Текущая карта является known-obstacle map, а не результатом SLAM.

#### `mission_planner_node`

Реализует высокоуровневую последовательность миссии:

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

Публикует смысловую цель:

```text
/drone/goal
```

Не должен управлять Allay напрямую и не должен публиковать `/drone/target`.

#### `path_planner_node`

Подписывается на:

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

Использует двумерный A*.

#### `drone_entity_controller_node`

Подписывается на:

```text
/drone/target
```

Через `/minecraft/command` выполняет команды `tp` для Allay.

Публикует:

```text
/drone/pose
/drone/path
/drone/controller_status
```

#### `player_camera_follow_node`

Читает `/drone/pose` и перемещает игрока со смещением относительно дрона.

Игрок — камера, а не дрон.

#### `sensor_monitor_node`

Используется для диагностики топиков игрока:

```text
/player/ground_truth
/player/imu
```

Не должен подменять `/drone/pose` данными игрока.

#### `visualizer_node`

Публикует RViz-маркеры:

```text
/drone/markers
```

Не должен влиять на движение или состояние миссии.

---

## 6. Интерфейсы и контракты между нодами

| Интерфейс | Издатель | Подписчик | Назначение |
|---|---|---|---|
| `/drone/goal` | `mission_planner_node` | `path_planner_node` | Высокоуровневая цель |
| `/drone/target` | `path_planner_node` | `drone_entity_controller_node` | Ближайшая точка пути |
| `/drone/pose` | `drone_entity_controller_node` | planner, mission, camera, visualizer | Текущая расчётная позиция Allay |
| `/drone/local_map` | `map_builder_node` | `path_planner_node`, RViz2 | Карта занятости |
| `/drone/planned_path` | `path_planner_node` | RViz2 | Полный A*-маршрут |
| `/drone/path` | `drone_entity_controller_node` | RViz2 | Фактическая траектория |
| `/drone/mission_state` | `mission_planner_node` | мониторинг | Состояние автомата |
| `/minecraft/command` | `minecraft_ros2` | world, spawn, controller, camera | Выполнение Minecraft-команд |

При добавлении новой ноды нельзя создавать второго активного издателя для `/drone/goal`, `/drone/target` или `/drone/pose`, если это не является явно спроектированным режимом переключения.

---

## 7. Система координат

Minecraft:

```text
X — горизонтальная ось
Y — высота
Z — горизонтальная ось
```

ROS-представление проекта:

```text
ROS x = Minecraft X
ROS y = Minecraft Z
ROS z = Minecraft Y
```

Горизонтальная карта строится в плоскости ROS `x-y`.

Высота хранится в ROS `z`.

Пример:

```text
Minecraft: X=10, Y=8, Z=4
ROS:       x=10, y=4, z=8
```

Правила:

1. Не смешивать Minecraft Y с ROS y.
2. Все преобразования координат должны быть централизованы в отдельных функциях.
3. Не дублировать формулы преобразования в нескольких местах без необходимости.
4. Все сообщения карты, путей, целей и маркеров должны использовать единый `frame_id`, обычно `map`.
5. Quaternion для нейтральной ориентации должен иметь `w=1.0`.

---

## 8. Ограничения текущей архитектуры

Claude обязан учитывать следующие ограничения:

1. Дрон — отдельная сущность Allay, а не игрок.
2. `/player/*` относится к игроку, а не к Allay.
3. `/drone/pose` является расчётной позицией контроллера, а не независимым ground truth измерением Allay.
4. Физика реального квадрокоптера не моделируется.
5. Движение реализовано дискретными командами `tp`.
6. Карта известна заранее.
7. SLAM и Nav2 не используются.
8. Планирование выполняется в 2D.
9. Препятствия считаются no-fly зонами независимо от возможности перелететь их по высоте.
10. Геометрия в `world_setup_node` и `map_builder_node` должна совпадать.
11. Стандартные сенсоры `minecraft_ros2` привязаны к игроку.
12. Minecraft должен быть запущен в графической сессии, а игрок должен находиться в загруженном мире.
13. `/minecraft/command` недоступен до корректного запуска мода и загрузки мира.
14. Запуск `world_setup_node` изменяет текущий Minecraft-мир и может уничтожить блоки в рабочей области.
15. Для экспериментов необходимо использовать отдельный Superflat-мир, а не важное пользовательское сохранение.

---

## 9. Особенности A*

Текущая логика планировщика:

- 2D occupancy grid;
- 8-связная сетка;
- стоимость прямого шага `1`;
- стоимость диагонального шага `sqrt(2)`;
- евклидова эвристика;
- выбор клетки с минимальным `f(n) = g(n) + h(n)`;
- запрет диагонального срезания углов;
- занятые клетки исключаются из поиска;
- вокруг препятствий добавляется safety margin;
- текущий safety margin обычно равен `2` клеткам;
- при разрешении `1.0` одна клетка соответствует одному Minecraft-блоку;
- маршрут периодически перепланируется;
- контроллер получает не весь маршрут, а lookahead-точку из `/drone/target`.

При изменении A* необходимо сохранить:

- допустимость эвристики;
- запрет прохода через занятые клетки;
- запрет corner cutting;
- корректную реконструкцию пути;
- обработку старта или цели, попавших в занятую клетку;
- публикацию пустого или диагностического результата при невозможности построить путь.

---

## 10. Настройка карты и мира

### 10.1. Простая настройка

Сначала искать параметры в:

```text
config/patrol_params.yaml
```

Перед изменением Claude должен определить, какие параметры реально читаются кодом:

```bash
rg "declare_parameter|get_parameter" minecraft_drone_coursework config launch
```

Нельзя считать параметр рабочим только потому, что он записан в YAML.

### 10.2. Синхронизация мира и occupancy grid

Критическое правило:

> Любое препятствие, созданное в Minecraft, должно существовать и в occupancy grid. Любое препятствие occupancy grid должно соответствовать реальному препятствию Minecraft.

Нельзя изменять только `world_setup_node.py` или только `map_builder_node.py`.

Для временного изменения необходимо обновить оба файла и проверить совпадение координат.

Для полноценной пользовательской настройки Claude должен предпочитать единственный источник данных:

```text
config/world.yaml
```

или эквивалентный общий конфигурационный файл.

Рекомендуемая модель данных:

```yaml
map:
  min_x: -25
  max_x: 25
  min_z: -25
  max_z: 25
  resolution: 1.0
  safety_margin_cells: 2

home:
  x: 0.0
  y: 8.0
  z: 0.0

obstacles:
  - name: wall_a
    min_x: 4
    max_x: 6
    min_z: -8
    max_z: 6
    min_y: 4
    max_y: 14

waypoints:
  - name: redstone
    x: 10.0
    y: 10.0
    z: 0.0
  - name: emerald
    x: 10.0
    y: 10.0
    z: 10.0

inspection:
  x: 19.0
  y: 10.0
  z: 19.0
  duration_sec: 5.0
```

Это пример целевой схемы, а не гарантия наличия файла.

При реализации такой схемы:

1. создать общий валидатор;
2. загружать один файл и в `world_setup_node`, и в `map_builder_node`;
3. проверять границы карты;
4. проверять, что `min <= max`;
5. проверять, что waypoint не находится внутри препятствия;
6. проверять, что home находится в свободной клетке;
7. выдавать понятную ошибку до изменения мира;
8. обновить launch-файл и README;
9. добавить unit-тесты для валидации.

### 10.3. Безопасность Minecraft-команд

Пользовательские строки не должны напрямую конкатенироваться в команды Minecraft без проверки.

Для координат:

- преобразовывать к `float` или `int`;
- проверять конечность через `math.isfinite`;
- ограничивать допустимый диапазон;
- форматировать числа явно.

Для имён:

- разрешать только безопасный набор символов;
- не вставлять пользовательский текст в selector или NBT без экранирования;
- не принимать произвольную команду от внешнего пользователя без явного запроса.

---

## 11. Настройка миссии

Текущая миссия задана конечным автоматом.

Для небольшого изменения допустимо менять координаты waypoint и порядок состояний в `mission_planner_node.py` и параметрах.

Для расширяемой пользовательской миссии следует перейти к конфигурации вида:

```yaml
mission:
  - type: goto
    name: redstone
    x: 10.0
    y: 10.0
    z: 0.0

  - type: wait
    duration_sec: 2.0

  - type: goto
    name: inspection
    x: 19.0
    y: 10.0
    z: 19.0

  - type: inspect
    duration_sec: 5.0

  - type: return_home

  - type: land
```

При добавлении конфигурируемой миссии необходимо:

- сохранить публикацию `/drone/goal`;
- сохранить `/drone/mission_state`;
- валидировать тип каждого шага;
- не позволять mission planner двигать Allay напрямую;
- обеспечить понятный статус ошибок;
- поддержать остановку или безопасное завершение миссии;
- добавить тесты переходов конечного автомата.

---

## 12. Интеграция пользовательских функций

Предпочтительный способ расширения — новая ROS 2-нода с чётким контрактом.

### 12.1. Новая функция анализа сенсоров

Новая нода может подписываться на:

```text
/player/image_raw
/player/imu
/player/pointcloud
/player/surrounding_block_array
```

Она не должна считать, что эти данные относятся к Allay.

Результат следует публиковать в новом namespaced-топике:

```text
/drone/perception/...
```

или предоставлять отдельный сервис.

### 12.2. Новый алгоритм планирования

Создавать отдельную реализацию с тем же контрактом:

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

Одновременно должен быть активен только один planner.

Переключение между planner-ами должно выполняться launch-параметром, а не ручным комментированием кода.

### 12.3. Новый алгоритм управления

Новый controller должен подписываться на `/drone/target` и публиковать `/drone/pose` и `/drone/path`.

Нельзя обходить path planner, публикуя Minecraft-команды прямо из mission planner.

### 12.4. Пользовательская команда дрону

Для пользовательского управления лучше добавить отдельный сервис, например:

```text
/drone/set_goal
/drone/pause
/drone/resume
/drone/emergency_stop
```

Сервис должен валидировать запрос и преобразовывать его в существующий pipeline.

Не следует предоставлять внешнему пользователю прямой неограниченный доступ к `/minecraft/command`.

### 12.5. Emergency stop

При добавлении emergency stop:

- controller прекращает отправку новых `tp`;
- текущая цель сбрасывается или замораживается;
- состояние публикуется явно;
- возобновление требует отдельной команды;
- stop имеет приоритет над mission planner и path planner;
- тестируется остановка во время движения.

---

## 13. Подготовка окружения

Ожидаемые строки окружения:

```bash
source /opt/ros/humble/setup.bash

export ROS2JAVA_INSTALL_PATH=$HOME/ros2_java_ws/install
source "$ROS2JAVA_INSTALL_PATH/setup.bash"

export ROS_DOMAIN_ID=0

source "$HOME/minecraft_drone_ws/install/setup.bash"
```

Claude не должен автоматически редактировать `~/.bashrc`.

Сначала выполнить диагностику:

```bash
source ~/.bashrc

echo "ROS_DISTRO=$ROS_DISTRO"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "ROS2JAVA_INSTALL_PATH=$ROS2JAVA_INSTALL_PATH"

which ros2
python3 --version
java -version
javac -version

ros2 pkg list | grep -E "rcljava|minecraft_msgs|minecraft_drone_coursework"
```

Ожидается:

```text
ROS_DISTRO=humble
ROS_DOMAIN_ID=0
Java 21
minecraft_msgs
minecraft_drone_coursework
```

Если окружение не настроено, Claude должен показать точные команды, но не изменять системные файлы без разрешения пользователя.

---

## 14. Сборка

Из workspace:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc

colcon build \
  --symlink-install \
  --packages-select minecraft_drone_coursework

source install/setup.bash
```

Для полной сборки workspace:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
colcon build --symlink-install
source install/setup.bash
```

После изменения:

- `setup.py`;
- `package.xml`;
- launch-файлов;
- config-файлов;
- console scripts;

необходимо повторить `colcon build`.

После изменений только Python-файлов `--symlink-install` обычно позволяет тестировать без полной переустановки, но Claude всё равно должен выполнить хотя бы синтаксическую проверку.

---

## 15. Запуск Minecraft

Minecraft требует графическую сессию.

Основная команда:

```bash
cd ~/minecraft_ros2
source ~/.bashrc
./runClient.sh
```

После запуска пользователь должен:

1. дождаться главного меню;
2. открыть отдельный Superflat-мир;
3. использовать Creative;
4. включить cheats;
5. дождаться полной загрузки мира.

Claude Code не должен утверждать, что Minecraft готов, только потому что процесс Java запущен.

Готовность подтверждается наличием сервиса:

```bash
ros2 service type /minecraft/command
```

и успешным вызовом:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'time set day'}"
```

### 15.1. Запуск из Claude Code

Перед запуском проверить:

```bash
echo "DISPLAY=$DISPLAY"
echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
```

Если графической сессии нет, Claude должен остановиться и сообщить, что Minecraft нельзя корректно поднять headless-командой.

Если доступен `gnome-terminal`, допустимо открыть отдельный терминал:

```bash
gnome-terminal \
  --title="Minecraft ROS 2" \
  -- bash -lc \
  'cd ~/minecraft_ros2 && source ~/.bashrc && ./runClient.sh; exec bash'
```

Не запускать Minecraft через `nohup` без вывода пользователю: окно игры всё равно требует GUI, а ошибки потеряются.

### 15.2. Ожидание сервиса

После входа пользователя в мир:

```bash
source ~/.bashrc

until ros2 service type /minecraft/command >/dev/null 2>&1; do
  echo "Waiting for /minecraft/command..."
  sleep 2
done

echo "/minecraft/command is available"
```

Устанавливать разумный timeout в автоматизированных скриптах, например 120 секунд.

---

## 16. Запуск проекта

После загрузки Minecraft-мира:

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
source install/setup.bash

ros2 launch \
  minecraft_drone_coursework \
  full_mission_astar.launch.py
```

Запуск в отдельном терминале:

```bash
gnome-terminal \
  --title="Minecraft Drone Mission" \
  -- bash -lc \
  'cd ~/minecraft_drone_ws && source ~/.bashrc && source install/setup.bash && ros2 launch minecraft_drone_coursework full_mission_astar.launch.py; exec bash'
```

Важно:

- `world_setup_node` изменяет мир;
- старая сущность `ros_drone` может быть удалена;
- RViz2 требует GUI;
- порядок запуска в launch-файле может использовать задержки;
- не заменять задержки без анализа зависимостей.

---

## 17. Проверка запущенной системы

### 17.1. ROS-граф

```bash
ros2 node list
ros2 topic list | sort
ros2 service list | sort
```

### 17.2. Критические ноды

```bash
ros2 node list | grep -E \
"world_setup|drone_spawn|map_builder|mission_planner|path_planner|drone_entity_controller|player_camera_follow|visualizer"
```

### 17.3. Критические топики

```bash
ros2 topic info /drone/pose
ros2 topic info /drone/goal
ros2 topic info /drone/target
ros2 topic info /drone/local_map
ros2 topic info /drone/planned_path
ros2 topic info /drone/mission_state
```

### 17.4. Мониторинг

```bash
ros2 topic echo /drone/mission_state
```

```bash
ros2 topic echo /drone/planner_status
```

```bash
ros2 topic echo --once /drone/pose
```

```bash
ros2 topic echo --once /drone/local_map
```

### 17.5. Частота публикации

```bash
ros2 topic hz /drone/pose
ros2 topic hz /player/imu
```

---

## 18. Запуск по частям

Подготовка мира:

```bash
ros2 run minecraft_drone_coursework world_setup_node
```

Создание дрона:

```bash
ros2 run minecraft_drone_coursework drone_spawn_node
```

Карта:

```bash
ros2 run minecraft_drone_coursework map_builder_node
```

Controller:

```bash
ros2 run minecraft_drone_coursework drone_entity_controller_node
```

Planner:

```bash
ros2 run minecraft_drone_coursework path_planner_node
```

Mission planner:

```bash
ros2 run minecraft_drone_coursework mission_planner_node
```

Камера:

```bash
ros2 run minecraft_drone_coursework player_camera_follow_node
```

Маркеры:

```bash
ros2 run minecraft_drone_coursework visualizer_node
```

Ручная цель:

```bash
ros2 topic pub --once \
  /drone/goal \
  geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'map'}, pose: {position: {x: 19.0, y: 19.0, z: 10.0}, orientation: {w: 1.0}}}"
```

При ручном тесте не запускать `mission_planner_node`, иначе он будет перезаписывать `/drone/goal`.

---

## 19. Остановка

Предпочтительный способ:

1. `Ctrl+C` в терминале ROS 2 launch.
2. Закрыть Minecraft штатно через меню.
3. При необходимости вернуть игрока в Creative:

```bash
ros2 service call \
  /minecraft/command \
  minecraft_msgs/srv/Command \
  "{command: 'gamemode creative @p'}"
```

Не использовать без необходимости:

```bash
pkill -9
killall java
git clean -fd
```

Claude не должен завершать все Java-процессы системы, так как это может затронуть другие приложения.

---

## 20. Тестирование

### 20.1. Синтаксическая проверка Python

Из корня пакета:

```bash
python3 -m compileall \
  minecraft_drone_coursework \
  launch
```

### 20.2. Сборка пакета

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc

colcon build \
  --symlink-install \
  --packages-select minecraft_drone_coursework
```

### 20.3. ROS 2 tests

```bash
cd ~/minecraft_drone_ws
source ~/.bashrc
source install/setup.bash

colcon test \
  --packages-select minecraft_drone_coursework

colcon test-result --verbose
```

Отсутствие тестов не считается успешной проверкой новой сложной логики.

### 20.4. Линтеры

Если зависимости установлены:

```bash
python3 -m pytest
python3 -m ruff check .
python3 -m black --check .
```

Не добавлять новый formatter или массово переформатировать весь проект без отдельного запроса.

### 20.5. Обязательные unit-тесты для новой логики

Для следующих компонентов предпочтительны тесты без Minecraft:

- world-to-grid и grid-to-world;
- преобразование Minecraft ↔ ROS;
- A* на маленьких картах;
- запрет corner cutting;
- поиск ближайшей свободной клетки;
- safety margin;
- валидация конфигурации;
- переходы mission state machine;
- выбор lookahead-точки;
- обработка недоступной цели;
- обработка пустой карты.

### 20.6. Smoke test с Minecraft

Перед smoke test предупредить пользователя, что мир будет изменён.

Checklist:

1. Minecraft открыт.
2. Пользователь находится в тестовом Superflat-мире.
3. `/minecraft/command` доступен.
4. `full_mission_astar.launch.py` запускается без traceback.
5. Появляется `ROS Drone`.
6. Публикуется `/drone/local_map`.
7. Публикуется `/drone/planned_path`.
8. Состояния миссии меняются.
9. Allay обходит препятствия.
10. RViz2 отображает карту и пути.
11. Миссия завершается состоянием `DONE`.

---

## 21. Правила написания Python-кода

### 21.1. Общие правила

- Python 3.10.
- PEP 8.
- Имена функций, переменных, файлов и топиков — на английском.
- Комментарии и документация могут быть на русском.
- Добавлять type hints для нетривиальных функций.
- Добавлять docstring для публичных классов и функций.
- Не использовать `print`; использовать `self.get_logger()`.
- Не использовать глобальное изменяемое состояние.
- Не смешивать ROS callback и сложный алгоритм в одной большой функции.
- Выносить математику и преобразования в чистые функции.
- Предпочитать небольшие, тестируемые функции.
- Обрабатывать ошибки сервисов и timeouts.
- Не подавлять исключения через пустой `except`.
- Не использовать `except Exception` без логирования и обоснования.
- Не добавлять зависимость без обновления `package.xml` и при необходимости `setup.py`.

### 21.2. Правила ROS 2

- Все пользовательские значения объявлять через `declare_parameter`.
- Считывать параметры один раз или использовать parameter callback осознанно.
- Имена топиков не хардкодить в нескольких нодах без необходимости.
- Использовать таймеры вместо бесконечных циклов внутри callback.
- Не выполнять долгие `sleep` внутри callback.
- Не блокировать executor длительным ожиданием сервиса.
- Для сервисов использовать timeout и проверять результат.
- Указывать `frame_id`.
- Обновлять `header.stamp`.
- Явно задавать QoS, если стандартный профиль недостаточен.
- Публиковать понятный status при ошибках.
- Корректно вызывать `destroy_node()` и `rclpy.shutdown()`.

### 21.3. Работа с Minecraft command service

Предпочтительно иметь общий helper:

```python
def call_minecraft_command(self, command: str) -> None:
    ...
```

Helper должен:

- ждать готовности сервиса с timeout;
- логировать отправляемую безопасную команду;
- обрабатывать `success=False`;
- обрабатывать exception future;
- не отправлять следующую критическую команду до завершения предыдущей;
- не создавать нового client на каждый вызов.

### 21.4. Логи

Использовать уровни:

- `debug` — частые внутренние вычисления;
- `info` — старт ноды, переход состояния, построенный путь;
- `warning` — временно отсутствующая карта или сервис;
- `error` — невозможность выполнить действие;
- `fatal` — продолжение работы небезопасно или невозможно.

Не печатать полный путь или pose на каждом timer tick в `info`, если это создаёт поток логов.

---

## 22. Правила launch-файлов

- Использовать `PathJoinSubstitution` и package share вместо абсолютных путей.
- Не хардкодить `/home/nikita` в репозитории.
- Передавать параметры через YAML.
- Новые режимы включать launch arguments.
- Для альтернативного planner/controller использовать условный запуск.
- Не запускать два издателя одного управляющего топика одновременно.
- Сохранять понятный порядок старта зависимых нод.
- Любую задержку `TimerAction` документировать.
- После изменения проверить:

```bash
ros2 launch minecraft_drone_coursework full_mission_astar.launch.py --show-args
```

---

## 23. Правила конфигурации

- Параметры, которые пользователь должен менять, хранить в `config/`.
- Не заставлять пользователя редактировать Python для изменения координаты.
- Единицы измерения указывать в имени или комментарии.
- Не смешивать Minecraft и ROS координаты без явного обозначения.
- Для новых параметров задавать безопасное значение по умолчанию.
- Валидировать параметры до отправки команд Minecraft.
- При несовместимом config завершать ноду с понятной ошибкой.
- Обновлять README при добавлении пользовательского параметра.

---

## 24. Файлы и директории, которые нельзя изменять

### 24.1. Строго запрещено изменять или коммитить

```text
.git/
build/
install/
log/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.pyc
```

Это служебные или сгенерированные файлы.

### 24.2. Внешние workspaces

Без явного запроса пользователя нельзя изменять:

```text
~/minecraft_ros2
~/ros2_java_ws
```

Особенно запрещено автоматически менять:

- Gradle wrapper;
- Forge version;
- Minecraft version;
- Java native library configuration;
- ARM64/LWJGL patches;
- сгенерированные Java ROS messages;
- `rcljava`;
- `minecraft_msgs`;
- Gradle cache.

Если проблема действительно находится во внешней зависимости, Claude должен:

1. доказать это диагностикой;
2. объяснить требуемое изменение;
3. запросить разрешение;
4. создать отдельный commit в соответствующем репозитории, если это отдельный Git repo.

### 24.3. Minecraft saves

Нельзя удалять или изменять напрямую:

```text
~/minecraft_ros2/run/saves/
```

Допускается изменение мира только через предусмотренные команды проекта и только после подтверждения, что пользователь находится в тестовом мире.

### 24.4. Пользовательское окружение

Без разрешения нельзя изменять:

```text
~/.bashrc
~/.profile
/etc/*
/opt/ros/*
```

Нельзя автоматически устанавливать или удалять системные пакеты.

### 24.5. Секреты

Нельзя создавать, читать в ответ или коммитить:

- GitHub PAT;
- SSH private keys;
- API keys;
- пароли;
- токены;
- `.env` с секретами;
- shell history с токенами.

При обнаружении секрета в tracked-файле остановиться и предупредить пользователя.

---

## 25. Защищённые core-файлы

Следующие файлы можно менять только когда задача этого требует:

```text
package.xml
setup.py
setup.cfg
launch/full_mission_astar.launch.py
config/patrol_params.yaml
rviz/minecraft_drone.rviz
```

Перед их изменением Claude должен:

1. объяснить, зачем изменение необходимо;
2. показать связанные места в коде;
3. сделать минимальный diff;
4. выполнить сборку;
5. проверить launch;
6. обновить README, если изменился пользовательский интерфейс.

`rviz/minecraft_drone.rviz` не редактировать вручную крупными массовыми заменами, так как формат чувствителен к структуре и отступам.

---

## 26. Git-правила

### 26.1. Перед началом работы

Обязательно:

```bash
git status --short
git branch --show-current
git log -5 --oneline
```

Если есть пользовательские незакоммиченные изменения:

- не удалять их;
- не перезаписывать связанные файлы без анализа;
- не делать `git checkout -- file`;
- не делать `git restore`;
- не делать `git reset --hard`;
- сначала показать пользователю конфликт.

### 26.2. Ветки

Новые крупные изменения выполнять в отдельной ветке:

```bash
git switch main
git pull --ff-only
git switch -c feature/<short-name>
```

Не выполнять `git pull` при наличии незакоммиченных изменений без согласования.

### 26.3. Коммиты

Коммиты должны быть:

- небольшими;
- тематическими;
- без unrelated изменений;
- с понятным imperative message.

Примеры:

```text
Add configurable world geometry
Validate mission waypoint configuration
Add emergency stop service
Document custom planner integration
```

Перед commit:

```bash
git diff --check
git status --short
git diff --stat
```

### 26.4. Запрещённые Git-действия

Без прямого запроса пользователя запрещено:

```bash
git reset --hard
git clean -fd
git push --force
git push --force-with-lease
git rebase --onto
git filter-repo
git commit --amend
```

Не удалять удалённые ветки и теги.

Не выполнять `git push`, пока пользователь не попросил отправить изменения или не подтвердил готовый commit.

### 26.5. .gitignore

В `.gitignore` должны быть исключены:

```gitignore
build/
install/
log/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.vscode/
.idea/
*.bag
*.db3
```

Не добавлять Minecraft saves, Gradle caches и логи.

---

## 27. Специальные инструкции для Claude Code

### 27.1. Обязательный алгоритм работы

Перед изменением Claude должен:

1. Определить корень repo:

```bash
git rev-parse --show-toplevel
```

2. Проверить состояние Git:

```bash
git status --short
```

3. Изучить структуру:

```bash
find . -maxdepth 3 -type f | sort
```

4. Прочитать:

```text
CLAUDE.md
README.md
package.xml
setup.py
launch/full_mission_astar.launch.py
config/patrol_params.yaml
```

5. Прочитать все ноды, которых касается задача.
6. Найти параметры и интерфейсы через `rg`.
7. Сформулировать краткий план.
8. Сделать минимальные изменения.
9. Запустить релевантные проверки.
10. Показать пользователю:
   - что изменено;
   - какие файлы;
   - какие тесты выполнены;
   - что не удалось проверить.

### 27.2. Не выдумывать состояние runtime

Claude не должен утверждать, что:

- Minecraft запущен;
- мир загружен;
- сервис доступен;
- Allay появился;
- RViz отображает данные;
- тест прошёл;

без фактической проверки.

Если GUI недоступен, нужно честно написать, что выполнены только статические проверки и сборка.

### 27.3. Долгоживущие процессы

При запуске Minecraft или ROS launch:

- не держать основной shell заблокированным без объяснения;
- использовать отдельный терминал или явно названную session;
- показывать пользователю команду остановки;
- сохранять лог только в согласованное место;
- не оставлять неизвестные фоновые процессы.

Перед повторным запуском проверять:

```bash
pgrep -af "runClient|minecraft|ros2 launch|rviz2"
```

Не завершать процессы автоматически, если непонятно, кому они принадлежат.

### 27.4. Диагностика до исправления

При ошибке сначала получить:

```bash
ros2 node list
ros2 topic list
ros2 service list
ros2 doctor --report
```

Для конкретной ноды:

```bash
ros2 node info /<node_name>
```

Для интерфейса:

```bash
ros2 topic info /<topic> -v
ros2 service type /<service>
ros2 interface show <type>
```

Для build:

```bash
colcon build \
  --event-handlers console_direct+ \
  --packages-select minecraft_drone_coursework
```

Не вносить случайные изменения до локализации причины.

### 27.5. Изменения должны быть обратимыми

- Маленький diff.
- Один логический шаг за раз.
- Сохранять работоспособный launch.
- Не переписывать весь файл, если достаточно изменить функцию.
- Не менять формат всех файлов ради одной функции.
- Не переименовывать публичные топики без миграции и обновления документации.

### 27.6. Документация

При изменении одного из следующих элементов обновить README:

- команды запуска;
- новая нода;
- новый топик или сервис;
- новый параметр;
- новая структура config;
- новая mission state;
- новый planner/controller;
- новое ограничение;
- изменение координат.

При архитектурном изменении обновить и этот `CLAUDE.md`.

---

## 28. Рекомендуемый план реализации пользовательской настройки

Когда пользователь просит «сделать карту настраиваемой», Claude должен идти по этапам.

### Этап 1. Анализ

Найти все hardcoded координаты:

```bash
rg \
"wall|obstacle|redstone|emerald|lapis|inspect|home_|min_x|max_x|min_z|max_z|fill |setblock " \
minecraft_drone_coursework config launch
```

### Этап 2. Единая схема

Создать один источник истины для:

- границ;
- разрешения;
- safety margin;
- препятствий;
- waypoint;
- home;
- inspection target;
- высот.

### Этап 3. Loader и validator

Вынести общую логику, например:

```text
minecraft_drone_coursework/world_config.py
```

Loader не должен зависеть от `rclpy`, чтобы его можно было unit-тестировать.

### Этап 4. Подключение мира

`world_setup_node` строит Minecraft-мир из config.

### Этап 5. Подключение карты

`map_builder_node` строит occupancy grid из тех же объектов.

### Этап 6. Подключение миссии

`mission_planner_node` получает waypoint из той же конфигурации или отдельного mission config.

### Этап 7. Валидация и тесты

Проверить:

- препятствия в bounds;
- start и goal свободны;
- имена уникальны;
- координаты конечны;
- маршрут существует хотя бы для базовой миссии;
- world и map получают идентичную геометрию.

### Этап 8. Документация

Добавить пример пользовательского config и команды запуска с ним.

---

## 29. Рекомендуемый план интеграции новой функции

Когда пользователь приносит свою функцию, Claude должен определить её слой:

| Функция | Правильное место |
|---|---|
| Создание блоков | `world_setup_node` или world config |
| Новая точка миссии | mission config / `mission_planner_node` |
| Новый поиск пути | отдельный planner |
| Новый закон движения | отдельный controller |
| Анализ изображения | perception node |
| Реакция на сенсор | отдельная behavior node |
| Новая визуализация | `visualizer_node` |
| Пользовательская команда | ROS service/action |
| Параметр движения | YAML parameter |

Затем:

1. определить входы;
2. определить выходы;
3. не обходить существующие слои;
4. выбрать тип сообщения;
5. добавить namespace;
6. добавить параметры;
7. добавить тест;
8. подключить через launch argument;
9. обновить README.

---

## 30. Критерии готовности изменения

Задача считается завершённой, когда выполнено применимое:

- код синтаксически корректен;
- пакет собирается;
- tests проходят;
- новые параметры валидируются;
- нет второго конфликтующего publisher;
- world geometry совпадает с occupancy grid;
- координаты преобразуются корректно;
- launch запускает нужный режим;
- новые файлы добавлены в `setup.py`/install rules;
- `package.xml` содержит зависимости;
- README обновлён;
- `git diff --check` не показывает ошибок;
- пользовательские изменения не потеряны;
- секреты и generated files не добавлены;
- для непроверенного GUI/runtime явно указано ограничение.

---

## 31. Быстрый сценарий Claude Code

```bash
# 1. Перейти в repo
cd ~/minecraft_drone_ws/src/minecraft_drone_coursework

# 2. Проверить Git
git status --short
git branch --show-current

# 3. Проверить окружение
source ~/.bashrc
echo "$ROS_DISTRO"
echo "$ROS_DOMAIN_ID"
java -version
ros2 pkg list | grep -E "minecraft_msgs|minecraft_drone_coursework"

# 4. Проверить код
python3 -m compileall minecraft_drone_coursework launch

# 5. Собрать
cd ~/minecraft_drone_ws
colcon build --symlink-install --packages-select minecraft_drone_coursework
source install/setup.bash

# 6. Запустить Minecraft в GUI
cd ~/minecraft_ros2
./runClient.sh

# 7. После входа пользователя в Superflat-мир проверить service
ros2 service type /minecraft/command

# 8. Запустить проект
cd ~/minecraft_drone_ws
ros2 launch minecraft_drone_coursework full_mission_astar.launch.py

# 9. Проверить миссию
ros2 topic echo /drone/mission_state
```

---

## 32. Главный принцип проекта

Сохранять следующую границу ответственности:

```text
Mission planner решает, КУДА лететь.
Path planner решает, КАКОЙ маршрут выбрать.
Controller решает, КАК двигаться к ближайшей точке.
minecraft_ros2 переносит команду в Minecraft.
Minecraft отображает результат.
RViz2 показывает инженерное состояние системы.
```

Новая функция должна интегрироваться в подходящий слой, а не объединять все уровни в одной ноде.
