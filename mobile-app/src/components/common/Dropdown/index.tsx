import { useTheme } from 'react-native-paper';
import { useState } from 'react';
import DropDownPicker, {
  ItemType,
  ValueType,
} from 'react-native-dropdown-picker';
import Ionicons from '@expo/vector-icons/Ionicons';
import { StyleProp, ViewStyle } from 'react-native';

type DropDownProps<T> = {
  onSelect?: (item: ItemType<T>) => void;
  initialValue: T;
  options: ItemType<T>[];
  multiple?: boolean;
  containerStyle?: StyleProp<ViewStyle>;
};

export default function DropDown<T extends ValueType>({
  onSelect,
  initialValue,
  options,
  containerStyle,
}: DropDownProps<T>) {
  const theme = useTheme();

  const [open, setOpen] = useState(false);
  const [value, setValue] = useState<T>(initialValue);
  const [items, setItems] = useState<ItemType<T>[]>(options);

  return (
    <DropDownPicker
      ArrowUpIconComponent={() => (
        <Ionicons
          name="arrow-up-outline"
          color={theme.colors.onPrimary}
          size={15}
        />
      )}
      containerStyle={containerStyle}
      ArrowDownIconComponent={() => (
        <Ionicons
          name="arrow-down-outline"
          color={theme.colors.onPrimary}
          size={15}
        />
      )}
      TickIconComponent={() => (
        <Ionicons
          name="checkmark-outline"
          size={15}
          color={theme.colors.onPrimary}
        />
      )}
      style={{
        backgroundColor: theme.colors.primary,
      }}
      listItemContainerStyle={{
        backgroundColor: theme.colors.primary,
      }}
      textStyle={{
        color: theme.colors.onPrimary,
      }}
      open={open}
      setOpen={setOpen}
      value={value}
      setValue={setValue}
      items={items}
      setItems={setItems}
      onSelectItem={onSelect}
    />
  );
}
