import { View, Text, TextInput, Button } from "react-native";
import React, { useState, useContext } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { cssInterop } from "nativewind";
import { REACT_APP_URL } from "@env";
import DropDownPicker from "react-native-dropdown-picker";
import RNDateTimePicker from "@react-native-community/datetimepicker";
import { AuthContext } from "../context/AuthContext";

cssInterop(SafeAreaView, { className: "style" });

const Create = () => {
  const { state } = useContext(AuthContext);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  //DATETIME
  const [date, setDate] = useState(new Date());
  const [show, setShow] = useState(false);
  const [mode, setMode] = useState("date");
  //SELECT STATUS
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("");
  const [items, setItems] = useState([
    { label: "Nierozpoczete", value: "not-started" },
    { label: "W trakcie", value: "in-progress" },
    { label: "Ukonczone", value: "done" },
  ]);

  const [isPosting, setIsPosting] = useState(false);

  const onChange = (e, selectedDate) => {
    setDate(selectedDate);
    setShow(false);
  };

  const showMode = (modeToShow) => {
    setShow(true);
    setMode(modeToShow);
  };

  const addPost = async () => {
    setIsPosting(true);
    const response = await fetch(`${REACT_APP_URL}/api/schedules/v1/tasks`, {
      method: "post",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.accessToken}`,
      },
      body: JSON.stringify({
        name: name,
        description: description,
        status: status,
        dueTo: date,
      }),
    }).catch((error) => {
      console.error(error);
    });
    setName("");
    setDescription("");
    setStatus("");
    setDate(new Date());
    setIsPosting(false);
  };
  return (
    <SafeAreaView>
      <Text className="text-3xl font-pbold text-purple-100 text-center">
        Create task
      </Text>
      <View className="my-10">
        <TextInput
          className="border-solid border-gray-100"
          placeholder="Nazwa"
          value={name}
          onChangeText={setName}
        ></TextInput>
        <TextInput
          className="border-solid border-gray-100"
          placeholder="Opis"
          value={description}
          onChangeText={setDescription}
        ></TextInput>
        <DropDownPicker
          placeholder="Wybierz status zadania"
          open={open}
          value={status}
          items={items}
          setOpen={setOpen}
          setValue={setStatus}
          setItems={setItems}
        />
        <Button title="Ustaw date" onPress={() => showMode("date")} />
        <Button title="Ustaw godzine" onPress={() => showMode("time")} />
        <Button
          title={isPosting ? "Dodawanie..." : "Dodaj zadanie"}
          onPress={addPost}
          disabled={isPosting}
        />
        {show && (
          <RNDateTimePicker
            mode={mode}
            display="spinner"
            value={date}
            onChange={onChange}
          />
        )}
      </View>
    </SafeAreaView>
  );
};

export default Create;
