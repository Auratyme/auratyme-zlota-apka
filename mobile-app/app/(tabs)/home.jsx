import { View, Text, TouchableOpacity } from "react-native";
import React, { useState, useContext } from "react";
import { Agenda, LocaleConfig } from "react-native-calendars";
import { SafeAreaView } from "react-native-safe-area-context";
import { cssInterop } from "nativewind";
import { REACT_APP_URL } from "@env";
import { format } from "date-fns";
import { useFocusEffect } from "@react-navigation/native";
import { AuthContext } from "../context/AuthContext";

cssInterop(SafeAreaView, { className: "style" });
LocaleConfig.locales["pl"] = {
  monthNames: [
    "Styczeń",
    "Luty",
    "Marzec",
    "Kwiecień",
    "Maj",
    "Czerwiec",
    "Lipiec",
    "Sierpień",
    "Wrzesień",
    "Październik",
    "Listopad",
    "Grudzień",
  ],
  monthNamesShort: [
    "Styc.",
    "Luty",
    "Marz.",
    "Kwiec.",
    "Maj",
    "Czer.",
    "Lip.",
    "Sier.",
    "Wrze.",
    "Paźd.",
    "Lis.",
    "Gru.",
  ],
  dayNames: [
    "Poniedzałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
  ],
  dayNamesShort: ["Pon.", "Wt.", "Śr.", "Czw.", "Pt.", "Sb.", "Nd."],
  today: "Dzisiaj",
};

LocaleConfig.defaultLocale = "pl";

const Home = () => {
  const { state } = useContext(AuthContext);
  const [items, setItems] = useState({});
  console.log(state.idToken);
  const fetchData = async () => {
    const response = await fetch(
      `${REACT_APP_URL}/api/schedules/v1/tasks?sortBy=asc&orderBy=dueTo`,
      {
        headers: {
          Authorization: `Bearer ${state.accessToken}`,
        },
      }
    );

    const data = await response.json();
    const mappedData = data.map((post) => {
      return {
        ...post,
        date: format(post.dueTo.slice(0, 10), "yyyy-MM-dd"),
      };
    });

    const reduced = mappedData.reduce((acc, currentItem) => {
      const { date, ...item } = currentItem;
      if (!acc[date]) {
        acc[date] = [];
      }
      acc[date].push(item);
      return acc;
    }, {});

    setItems(reduced);
  };

  useFocusEffect(
    React.useCallback(() => {
      fetchData();
    }, [])
  );

  const renderDay = (item) => {
    return (
      <SafeAreaView>
        <TouchableOpacity>
          <View className="flex-row items-center bg-primary rounded-md p-4 mx-8">
            <View className="bg-blue w-2 h-full rounded-full"></View>
            <View className="flex-row justify-between items-center w-full">
              <View className="w-4/5">
                <Text className="text-xl font-pmedium text-white mx-5">
                  {item.name}
                </Text>
                <Text className="text-xs font-plight text-white mx-5">
                  {item.description}
                </Text>
              </View>
              <TouchableOpacity
                onPress={(e) => {
                  fetch(`${REACT_APP_URL}/api/schedules/v1/tasks/${item.id}`, {
                    method: "delete",
                    headers: {
                      Authorization: `Bearer ${state.accessToken}`,
                    },
                  })
                    .then((response) => {
                      if (!response.ok) {
                        throw new Error("Something went wrong");
                      }
                      fetchData();
                    })
                    .catch((e) => {
                      console.log(e);
                    });
                }}
              >
                <Text>Usuń</Text>
              </TouchableOpacity>
              <Text className="font-plight text-sm text-white w-1/5">
                {item.dueTo.slice(10, 16)}
              </Text>
            </View>
          </View>
        </TouchableOpacity>
      </SafeAreaView>
    );
  };

  let currentDate = new Date().toJSON().slice(0, 10);

  return (
    <View className="flex-1">
      <Agenda
        items={items}
        selected={currentDate}
        renderItem={renderDay}
        theme={{
          selectedDayBackgroundColor: "#7b1ad1",
          todayTextColor: "#7b1ad1",
          dotColor: "#7b1ad1",
          calendarBackground: "#161616",
          agendaDayTextColor: "white",
          backgroundColor: "#161616",
        }}
      />
    </View>
  );
};

export default Home;
