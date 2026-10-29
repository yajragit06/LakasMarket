import { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import type { Listing } from "@lakasmarket/shared";
import { api } from "../api";

export function BrowseScreen() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listListings()
      .then(setListings)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Active listings</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={listings}
        keyExtractor={(l) => String(l.id)}
        ListEmptyComponent={<Text style={styles.muted}>No listings yet.</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.title}>{item.title}</Text>
            <Text style={styles.seller}>
              {item.seller.display_name} · Adab {item.seller.adab_score.toFixed(0)}/100
            </Text>
            <Text style={styles.price}>B$ {Number(item.list_price).toFixed(2)}</Text>
            <Text style={styles.floor}>
              Offers below B$ {item.hard_floor_price.toFixed(2)} are auto-declined.
            </Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: "#f6f7f9" },
  header: { fontSize: 20, fontWeight: "700", marginBottom: 12, color: "#1a1a1a" },
  card: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#e4e7eb",
    borderRadius: 10,
    padding: 16,
    marginBottom: 12,
  },
  title: { fontSize: 16, fontWeight: "600" },
  seller: { fontSize: 13, color: "#4a5568", marginTop: 2 },
  price: { fontSize: 18, fontWeight: "700", marginTop: 6 },
  floor: { fontSize: 12, color: "#8a1f1f", marginTop: 2 },
  muted: { color: "#4a5568" },
  error: { color: "#8a1f1f", marginBottom: 12 },
});
