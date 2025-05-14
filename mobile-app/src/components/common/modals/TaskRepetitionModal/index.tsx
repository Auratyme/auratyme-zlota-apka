import { FlatList, View } from 'react-native';

import { ReactElement, useEffect, useState } from 'react';
import {
  Button,
  Text,
  TextInput,
  Modal,
  Portal,
  useTheme,
  ToggleButton,
} from 'react-native-paper';
import { DropDown } from '@/src/components/common';
import { ItemType } from 'react-native-dropdown-picker';
import { IconSource } from 'react-native-paper/lib/typescript/components/Icon';
import { TimePickerModal } from 'react-native-paper-dates';
import { CronTime } from 'cron-time-generator';

type StatefulToggleButtonProps = {
  icon: IconSource;
  onPress?: (checked: boolean) => void;
};

function StatefulToggleButton({ icon, onPress }: StatefulToggleButtonProps) {
  const [checked, setChecked] = useState<boolean>(false);

  return (
    <ToggleButton
      status={checked ? 'checked' : 'unchecked'}
      onPress={() => {
        setChecked(!checked);
        if (onPress) onPress(checked);
      }}
      icon={icon}
    />
  );
}

type RepeatModalProps = {
  visible: boolean;
  onDismiss?: () => void;
  onConfirm?: (cron: string) => void;
};

export default function TaskRepetitionModal({
  visible,
  onDismiss,
  onConfirm,
}: RepeatModalProps) {
  type Every = 'day' | 'week' | 'hour' | 'minute';

  const everyOptions: ItemType<Every>[] = [
    { label: 'day(s)', value: 'day' },
    { label: 'week(s)', value: 'week' },
    { label: 'hour(s)', value: 'hour' },
    { label: 'minute(s)', value: 'minute' },
  ];

  const theme = useTheme();
  const [timeModalVisible, setTimeModalVisible] = useState<boolean>(false);
  const [additionalConfig, setAdditionalConfig] = useState<ReactElement | null>(
    null
  );

  const [every, setEvery] = useState<Every>('day');
  const [weekdays, setWeekdays] = useState<number[]>([0]);
  const [time, setTime] = useState<Date | null>(null);
  const [cron, setCron] = useState<string | null>(null);
  const [count, setCount] = useState<number>(1);

  const weekdayIcons = [
    'alpha-m',
    'alpha-t',
    'alpha-w',
    'alpha-t',
    'alpha-f',
    'alpha-s',
    'alpha-s',
  ];

  useEffect(() => {
    switch (every) {
      case 'day': {
        setAdditionalConfig(
          <Button
            icon="clock"
            className="flex-row justify-start"
            onPress={() => {
              setTimeModalVisible(true);
            }}
          >
            <Text variant="bodyLarge">
              {time
                ? time.toLocaleTimeString('pl', {
                    timeStyle: 'short',
                  })
                : 'Add time'}
            </Text>
          </Button>
        );

        break;
      }

      case 'week': {
        setAdditionalConfig(
          <View>
            <FlatList
              data={[0, 1, 2, 3, 4, 5, 6, 7]}
              horizontal
              renderItem={(item) => {
                return (
                  <StatefulToggleButton
                    icon={weekdayIcons[item.index]}
                    onPress={(checked) => {
                      if (!checked) {
                        setWeekdays([...weekdays, item.index]);
                      } else {
                        setWeekdays(
                          weekdays.filter((weekday) => weekday != item.index)
                        );
                      }
                    }}
                  />
                );
              }}
            />
            <Button
              icon="clock"
              className="flex-row justify-start"
              onPress={() => {
                setTimeModalVisible(true);
              }}
            >
              <Text variant="bodyLarge">
                {time
                  ? time.toLocaleTimeString('pl', {
                      timeStyle: 'short',
                    })
                  : 'Add time'}
              </Text>
            </Button>
          </View>
        );

        break;
      }

      case 'hour': {
        setAdditionalConfig(null);
        break;
      }

      case 'minute': {
        setAdditionalConfig(null);
        break;
      }
    }
  }, [every]);

  return (
    <Portal>
      <Modal
        contentContainerStyle={{
          backgroundColor: theme.colors.background,
          padding: 20,
          margin: 20,
          display: 'flex',
          gap: 20,
        }}
        visible={visible}
        onDismiss={() => {
          if (onDismiss) onDismiss();
        }}
      >
        <Text variant="titleLarge">Set repetition</Text>
        <View className="gap-4">
          <Text variant="bodyLarge">Every: </Text>
          <View className="flex-row items-center gap-4">
            <TextInput
              defaultValue="1"
              inputMode="numeric"
              mode="outlined"
              onChangeText={(text) => {
                setCount(parseInt(text));
              }}
            />
            <DropDown
              initialValue={'day'}
              options={everyOptions}
              onSelect={(item) => {
                if (item.value) setEvery(item.value);
              }}
            />
          </View>
          {additionalConfig}
        </View>
        <Button
          mode="contained"
          onPress={() => {
            let newCron: string | null = null;

            switch (every) {
              case 'day': {
                newCron = CronTime.every(count).days(
                  time?.getHours(),
                  time?.getMinutes()
                );

                break;
              }

              case 'week': {
                newCron = CronTime.everyWeekAt(
                  weekdays,
                  time?.getHours(),
                  time?.getMinutes()
                );

                break;
              }

              case 'hour': {
                newCron = CronTime.every(count).hours();

                break;
              }

              case 'minute': {
                newCron = CronTime.every(count).minutes();

                break;
              }
            }

            setCron(newCron);

            if (onConfirm) onConfirm(newCron);
          }}
        >
          Save
        </Button>
        <TimePickerModal
          visible={timeModalVisible}
          onDismiss={() => {
            setTimeModalVisible(false);
          }}
          onConfirm={(time) => {
            const newTime = new Date();
            newTime.setHours(time.hours);
            newTime.setMinutes(time.minutes);

            setTime(newTime);

            setTimeModalVisible(false);
          }}
          use24HourClock
        />
      </Modal>
    </Portal>
  );
}
