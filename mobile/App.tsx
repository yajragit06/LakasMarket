import { useState } from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import { LoginScreen } from "./src/screens/LoginScreen";
import { BrowseScreen } from "./src/screens/BrowseScreen";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      {loggedIn ? <BrowseScreen /> : <LoginScreen onLoggedIn={() => setLoggedIn(true)} />}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f6f7f9" },
});
