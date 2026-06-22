import random
import os
import time
import hashlib
import sys
import json

class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    MAGENTA = '\033[35m' # Legendary Artifact Color
    GRAY = '\033[38;5;239m'
    RESET = '\033[0m'

class TradeTycoon:
    def __init__(self):
        # --- PYINSTALLER SAFE PATH LOGIC ---
        if getattr(sys, 'frozen', False):
            # If running as a compiled .exe, get the path of the .exe itself
            application_path = os.path.dirname(sys.executable)
        else:
            # If running normally through Python, get the path of this script
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.save_file = os.path.join(application_path, "trade_tycoon_save.json")

        # New Global Variables to allow pagination during inputs
        self.display_items = []
        self.total_pages = 1

        # Trigger the initial state on load with default values
        self.reset_game_state()

    def reset_game_state(self, bonus_gp=0, kept_artifact=None, kept_qty=0):
        # --- Single Source of Truth for Game Variables ---
        self.run_id = random.randint(99999, 9999999)
        self.money = 10000 + bonus_gp
        self.week = 1
        self.unlock_cost = 500000
        self.unlocked_count = 0
        self.total_score = 0
        self.current_events = []

        # --- ACTION ECONOMY TRACKERS ---
        self.buys_remaining = 1
        self.sells_remaining = 1

        self.current_page = 0
        self.event_scroll = 0 # <-- Added to track event log scrolling

        self.active_items = ["Arrows", "Beer", "Blankets", "Candles", "Cloth", "Coal", "Flour", "Glass", "Herbs", "Leather", "Mirrors", "Rations", "Sardines", "Sea Salt", "Slaves", "Stone", "Torches", "Waterskin", "Wheat", "Wood"]

        self.locked_items = ["Adamantine", "Amber", "Amethyst", "Antitoxin", "Armor", "Bag of Holding", "Banana", "Beef", "Beeswax", "Berries", "Cassava", "Cattle", "Cat Memes", "Cheese", "Chlorophyte", "Cinnamon", "Cocoa", "Cod", "Coffee", "Compass of True North", "Coral", "Crown Jewel", "Cryptocurrency", "Daggers", "Diamond", "Dimensional Pinball Machine", "Dragon Scales", "Dream Dust", "Emerald", "Everlasting Gobstopper", "Flint & Steel", "Frankincense", "Fur", "Glitterstim", "Glowcopper", "Gold", "Gunpowder", "Honey", "Horses", "Indigo", "Invisibility Cloak", "Iron", "Ivory", "Lamb", "Lavastone", "Lead", "Lightsaber", "Lucky Dice", "Mackerel", "Mango", "Mercury", "Meteorite", "Mithril", "Myrrh", "Nanites", "Oats", "Obsidian", "Olive Oil", "Olives", "Orichalum", "Palladium", "Paprika", "Parchment", "Pearls", "Pepper", "Philosopher Stones", "Phoenix Feather", "Poison", "Pork", "Potions", "Pottery", "Romulan Ale", "Rope", "Ruby", "Safety Deposit Box", "Sapphire", "Scrolls", "Shadow Lantern", "Sheep", "Silk", "Silver", "Sleeper Agents", "Sunstone", "Swordfish", "Swords", "Time Machine", "Tin", "Titanium", "Tobacco", "Topaz", "Tuna", "Vorpal Blades", "Whisperwind Cloak"]

        # Auto-alphabetize the locked items
        self.locked_items.sort()

        self.artifacts = ["Smuggler's Writ", "Black Swan Catalyst", "Political Favors", "Owl-Chemist"]
        self.current_hash = ""
        self.artifact_stock = {}

        self.inventory = {item: 0 for item in self.active_items}
        self.average_cost = {item: 0 for item in self.active_items}

        for art in self.artifacts:
            self.inventory[art] = 0
            self.average_cost[art] = 0

        # Inject the hoarded stack if Prestige arguments were passed
        if kept_artifact and kept_qty > 0:
            self.inventory[kept_artifact] = kept_qty

        self.current_market = []
        self.market_prices = {}

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_keypress(self):
        """ Silently captures a single keypress, preserving special keys and standard case. """
        if os.name == 'nt': # Windows handling
            import msvcrt
            key = msvcrt.getch()
            if key in (b'\x00', b'\xe0'):
                special = msvcrt.getch()
                if special == b'K': return 'left'
                if special == b'M': return 'right'
                if special == b'H': return 'up'
                if special == b'P': return 'down'
                if special == b'S': return 'delete'
                return ''
            if key in (b'\r', b'\n'): return 'enter'
            if key == b'\x08': return 'backspace'
            if key == b'\x03': raise KeyboardInterrupt
            try:
                return key.decode('utf-8')
            except:
                return ''
        else: # Unix/Linux/Mac handling
            import tty, termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                # Arrow keys send an escape sequence starting with \x1b
                if ch == '\x1b':
                    ch2 = sys.stdin.read(2)
                    if ch2 == '[D': return 'left'
                    if ch2 == '[C': return 'right'
                    if ch2 == '[A': return 'up'
                    if ch2 == '[B': return 'down'
                    if ch2 == '[3':
                        sys.stdin.read(1)
                        return 'delete'
                    return ''
                if ch in ('\r', '\n'): return 'enter'
                if ch in ('\x08', '\x7f'): return 'backspace'
                if ch == '\x03': raise KeyboardInterrupt
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch

    def get_price_color(self, price):
        max_price = 255 + (self.unlocked_count * 5)
        halfway = max_price / 2.0

        p = min(max(int(price), 1), max_price)

        if p <= halfway:
            r = int((p / halfway) * 255)
            g = 255
        else:
            r = 255
            g = int(255 - (((p - halfway) / (max_price - halfway)) * 255))

        b = 0
        return f"\033[38;2;{r};{g};{b}m"

    def get_market_hash(self, seed_string, seed_string_two):
        hash1 = hashlib.sha512(seed_string.encode()).hexdigest()
        hash2 = hashlib.sha512(seed_string_two.encode()).hexdigest()
        hash3 = hashlib.sha512((seed_string + "_expansion").encode()).hexdigest()
        hash4 = hashlib.sha512((seed_string_two + "_expansion").encode()).hexdigest()
        return hash1 + hash2 + hash3 + hash4

    def sync_artifact_prices(self):
        """Ensures all artifacts on the market perfectly match the sum of all normal items."""
        artifact_price = sum(price for item, price in self.market_prices.items() if item not in self.artifacts)
        for art in self.artifacts:
            if art in self.market_prices:
                self.market_prices[art] = max(1, artifact_price)

    def roll_for_artifact(self, market_hash, is_grand_market=False):
        # --- SEED-LOCKED ARTIFACT GENERATION ---
        if int(market_hash[0:2], 16) < 80: # <-- Controls how often artifacts spawn
            spawned_artifact = random.choice(self.artifacts)

            self.current_market.append(spawned_artifact)
            self.market_prices[spawned_artifact] = 0 # Initialized to 0, synced globally right after
            self.artifact_stock[spawned_artifact] = 10 # <-- Controls the number of artifacts in each spawn

            market_type = "GRAND MARKET" if is_grand_market else "MARKET"
            self.current_events.append(f"A LEGENDARY ARTIFACT HAS APPEARED IN THE {market_type}: {spawned_artifact}")

    def generate_market(self):
        self.current_events = []

        self.current_market = []
        self.market_prices = {}
        self.artifact_stock = {}
        total_artifacts = sum(self.inventory.get(art, 0) for art in self.artifacts)

        seed_string = f"run_{self.run_id}_money_{self.money}_score_{self.total_score}_unlocked_{self.unlocked_count}_arts_{total_artifacts}_week_{self.week}"
        seed_string_two = f"run_{self.run_id}_week_{self.week}_score_{self.total_score}_unlocked_{self.unlocked_count}_money_{self.money}"

        # Pass BOTH strings into the function
        market_hash = self.get_market_hash(seed_string, seed_string_two)

        self.current_hash = market_hash

        shuffled = random.sample(self.active_items, len(self.active_items))
        market_size = random.randint(8, 15)
        if market_size > len(self.active_items):
            market_size = len(self.active_items)

        for i in range(market_size):
            item = shuffled[i]
            self.current_market.append(item)
            hex_pair = market_hash[i*2 : (i*2)+2]
            raw_hash_price = int(hex_pair, 16)
            scaling_bonus = self.unlocked_count * 5
            self.market_prices[item] = max(1, raw_hash_price + scaling_bonus)

        self.roll_for_artifact(market_hash)
        self.sync_artifact_prices()
        self.current_market.sort()

    def trigger_event(self):
        # --- NEW EVENT POOL LOGIC ---
        event_pool = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        for _ in range(5): # Maximum of 5 events per week
            # 50% chance to stop drawing events immediately
            if random.randint(0, 1) == 0:
                break

            if not event_pool:
                break # Break if we somehow exhaust the entire pool

            # Draw a unique event and remove it from the pool to prevent duplicates
            chosen_event = random.choice(event_pool)
            event_pool.remove(chosen_event)

            if chosen_event == 1:
                # 1. GRAND MARKET
                missing_items = [item for item in self.active_items if item not in self.current_market]
                normal_item_count = len([m for m in self.current_market if m not in self.artifacts])

                total_artifacts = sum(self.inventory.get(art, 0) for art in self.artifacts)

                seed_string = f"run_{self.run_id}_money_{self.money}_score_{self.total_score}_unlocked_{self.unlocked_count}_arts_{total_artifacts}_week_{self.week}"
                seed_string_two = f"run_{self.run_id}_week_{self.week}_score_{self.total_score}_unlocked_{self.unlocked_count}_money_{self.money}"

                market_hash = self.get_market_hash(seed_string, seed_string_two)

                self.current_hash = market_hash

                for item in missing_items:
                    self.current_market.append(item)
                    hex_pair = self.current_hash[normal_item_count*2 : (normal_item_count*2)+2]
                    raw_hash_price = int(hex_pair, 16)
                    scaling_bonus = self.unlocked_count * 5
                    self.market_prices[item] = max(1, raw_hash_price + scaling_bonus)
                    normal_item_count += 1

                self.roll_for_artifact(market_hash, is_grand_market=True)
                self.current_market.sort()
                grand_msgs = [
                        "GRAND MARKET DAY! Merchants from all realms have gathered. Everything is available!",
                        "FESTIVAL OF COINS! The King declared a tax-free holiday! All goods are trading today!",
                        "TRADE FLEET ARRIVES! Hundreds of ships just docked. The market is completely flooded with goods!"
                    ]
                self.current_events.append(random.choice(grand_msgs))

            elif chosen_event == 2:
                # 2. MARKET BOOM
                targets = [m for m in self.current_market if m not in self.artifacts]
                if targets:
                    e_item = random.choice(targets)
                    self.market_prices[e_item] = int(self.market_prices[e_item] ** (1 + (self.week / 13.33)))
                    boom_msgs = [
                        f"MARKET BOOM! A local lord is hoarding {e_item}. Prices are sky high!",
                        f"MARKET BOOM! 'Castle's Got Talent' bought all the {e_item}! Prices are sky high!",
                        f"MARKET BOOM! Doomsday predictions caused a sudden shortage of {e_item}! Prices are sky high!"
                    ]
                    self.current_events.append(random.choice(boom_msgs))

            elif chosen_event == 3:
                # 3. MARKET CRASH
                targets = [m for m in self.current_market if m not in self.artifacts]
                if targets:
                    e_item = random.choice(targets)
                    self.market_prices[e_item] = 1
                    crash_msgs = [
                        f"MARKET CRASH! A massive surplus of {e_item} has flooded the market!",
                        f"MARKET CRASH! The King suddenly outlawed {e_item}! Merchants are dumping their stock!",
                        f"MARKET CRASH! Someone claimed Sand can be used in place of {e_item}. The {e_item} market crashes during this idiotic time."
                    ]
                    self.current_events.append(random.choice(crash_msgs))

            elif chosen_event == 4:
                # 4. FORTUNE (COIN)
                found = (random.randint(50, 1500) * self.week) + (self.unlocked_count * 200)
                self.money += found
                gold_msgs = [
                    f"MONEY! You found a discarded coin purse containing ${found:,} on the floor of your store.",
                    f"MONEY! A grateful noble tipped you ${found:,} for giving them good financial advice.",
                    f"MONEY! You won a tavern bet against a drunken knight and walked away with ${found:,}!"
                ]
                self.current_events.append(random.choice(gold_msgs))

            elif chosen_event == 5:
                # 5. FORTUNE (UNLOCKED ITEMS)
                f_item = random.choice(self.active_items)
                f_qty = (random.randint(50, 100) * self.week) + (self.unlocked_count * 5)
                current_qty = self.inventory[f_item]
                current_avg = self.average_cost[f_item]
                current_total_value = current_qty * current_avg
                new_qty = current_qty + f_qty
                self.average_cost[f_item] = current_total_value // new_qty if new_qty > 0 else 0
                self.inventory[f_item] = new_qty
                item_msgs = [
                    f"FORTUNE! You discovered an overturned wagon and salvaged {f_qty:,} {f_item}!",
                    f"FORTUNE! You found a hidden smuggler's cache containing {f_qty:,} {f_item}!"
                ]
                self.current_events.append(random.choice(item_msgs))

            elif chosen_event == 6:
                # 6. BONUS (LOCKED ITEMS)
                if self.locked_items:
                    f_item = random.choice(self.locked_items)
                else:
                    f_item = random.choice(self.active_items)

                f_qty = (random.randint(50, 100) * self.week) + (self.unlocked_count * 5)
                if f_item not in self.inventory:
                    self.inventory[f_item] = 0
                    self.average_cost[f_item] = 0

                current_qty = self.inventory.get(f_item, 0)
                current_avg = self.average_cost.get(f_item, 0)
                current_total_value = current_qty * current_avg
                new_qty = current_qty + f_qty
                self.average_cost[f_item] = current_total_value // new_qty if new_qty > 0 else 0
                self.inventory[f_item] = new_qty
                magic_msgs = [
                    f"KAZAAM! A mischievous forest fairy gifted you {f_qty:,} {f_item}!",
                    f"KAZAAM! You rubbed a strange lamp and you got {f_qty:,} {f_item}!"
                ]
                self.current_events.append(random.choice(magic_msgs))

            elif chosen_event == 7:
                # 7. GUILD SUBSIDY
                if self.locked_items:
                    self.unlock_cost = self.unlock_cost // 50
                    if self.unlock_cost < 10000:
                        self.unlock_cost = 10000
                    guild_good_msgs = [
                        "GUILD SUBSIDY! The Merchant's Guild is subsidizing permits. Unlock costs reduced!",
                        "ROYAL DECREE! The King wants more trade! Unlock fees are slashed!"
                    ]
                    self.current_events.append(random.choice(guild_good_msgs))
                else:
                    self.current_events.append("The Guild has no more items to offer you...")

            elif chosen_event == 8:
                # 8. GUILD MONOPOLY
                if self.locked_items:
                    self.unlock_cost = int(self.unlock_cost * 1.5)
                    guild_bad_msgs = [
                        "GUILD MONOPOLY! The Merchant's Guild has restricted trade. Unlock costs have surged!",
                        "INFLATION! A poor harvest has driven up the price of everything, including unlock fees!"
                    ]
                    self.current_events.append(random.choice(guild_bad_msgs))
                else:
                    self.current_events.append("The Guild has no more items to offer you...")

            elif chosen_event == 9:
                # 9. AMBUSH (ITEMS)
                owned_items = [item for item, qty in self.inventory.items() if qty > 0 and item not in self.artifacts]
                if owned_items:
                    s_item = random.choice(owned_items)
                    current_qty = self.inventory[s_item]
                    lost_qty = random.randint(1, 49) + self.week + (self.unlocked_count * 10)
                    if lost_qty > current_qty:
                        lost_qty = current_qty
                    self.inventory[s_item] -= lost_qty
                    if self.inventory[s_item] == 0:
                        self.average_cost[s_item] = 0
                    item_ambush_msgs = [
                        f"AMBUSH! Bandits raided your shop and made off with {lost_qty:,} {s_item}!",
                        f"AMBUSH! Rats got into your supplies and ruined {lost_qty:,} {s_item}!"
                    ]
                    self.current_events.append(random.choice(item_ambush_msgs))
                else:
                    item_ambush_msgs = [
                        f"LUCKY BREAK! Bandits raided your shop but couldn't find anything to steal!",
                        f"LUCKY BREAK! Rats got into your supplies but you exterminated them before they did any damage!"
                    ]
                    self.current_events.append(random.choice(item_ambush_msgs))

            elif chosen_event == 10:
                # 10. AMBUSH (COINS)
                lost = random.randint(50, 500) + 100 + (self.unlocked_count * 200)
                if self.money < lost:
                    lost = self.money
                self.money -= lost
                gold_ambush_msgs = [
                    f"AMBUSH! Bandits raided your shop in the night. You lost ${lost:,}.",
                    f"AMBUSH! Pickpockets swarmed you in the crowded town square! You lost ${lost:,}."
                ]
                self.current_events.append(random.choice(gold_ambush_msgs))

        # --- NEW MASTER RECALCULATION ---
        # After all events resolve, ensure all artifacts match the final sum of the market!
        self.sync_artifact_prices()

    def print_2_columns(self, items, formatter, start_idx=0):
        num_items = len(items)
        if num_items == 0:
            print("  (Empty)")
            return
        rows = (num_items + 1) // 2
        for r in range(rows):
            line = "  "
            for col in range(2):
                idx = r + (col * rows)
                if idx < num_items:
                    # Pass the absolute index (start_idx + idx) so the numbering is always correct!
                    line += formatter(start_idx + idx, items[idx]) + "    "
            print(line.rstrip())

    def print_3_columns(self, items, formatter):
        num_items = len(items)
        if num_items == 0:
            print("  (Empty)")
            return
        rows = (num_items + 2) // 3
        for r in range(rows):
            line = "  "
            for col in range(3):
                idx = r + (col * rows)
                if idx < num_items:
                    line += formatter(idx, items[idx]) + " "
            print(line.rstrip())

    def parse_qty(self, user_input, max_qty):
        val = user_input.lower().strip()
        if val in ['a', 'all']: return max_qty
        if val in ['h', 'half']: return max_qty // 2
        if val in ['q', 'quarter']: return max_qty // 4
        try:
            qty = int(val)
            return qty if qty > 0 else 0
        except ValueError:
            return 0

    # --- SAVE / LOAD METHODS ---
    def save_game(self):
        save_data = {
            "run_id": self.run_id,
            "money": self.money,
            "week": self.week,
            "unlock_cost": self.unlock_cost,
            "unlocked_count": self.unlocked_count,
            "total_score": self.total_score,
            "buys_remaining": self.buys_remaining,
            "sells_remaining": self.sells_remaining,
            "active_items": self.active_items,
            "inventory": self.inventory,
            "average_cost": self.average_cost,
            "artifact_stock": self.artifact_stock,
            "current_market": self.current_market,
            "market_prices": self.market_prices,
            "current_hash": self.current_hash,
            "current_events": self.current_events
        }
        try:
            with open(self.save_file, "w") as f:
                json.dump(save_data, f, indent=4)
            self.current_events.append("GAME SAVED SUCCESSFULLY!")
        except Exception as e:
            self.current_events.append(f"ERROR SAVING GAME: {e}")

    def load_game(self):
        try:
            with open(self.save_file, "r") as f:
                save_data = json.load(f)

            # 1. Load the base numerical variables
            self.run_id = save_data.get("run_id", random.randint(100000, 999999))
            self.money = save_data.get("money", self.money)
            self.week = save_data.get("week", self.week)
            self.unlock_cost = save_data.get("unlock_cost", self.unlock_cost)
            self.total_score = save_data.get("total_score", self.total_score)
            self.unlocked_count = save_data.get("unlocked_count", self.unlocked_count)
            self.buys_remaining = save_data.get("buys_remaining", 1)
            self.sells_remaining = save_data.get("sells_remaining", 1)
            self.current_page = 0 # Reset pagination on load
            self.event_scroll = 0 # Reset event scroll on load

            # 2. Preserve Randomized Unlocks & Forward Compatibility
            self.active_items = save_data.get("active_items", self.active_items)

            # Filter the master script list so any item we already unlocked is erased from locked_items
            self.locked_items = [item for item in self.locked_items if item not in self.active_items]
            self.locked_items.sort()

            # 3. Load the dictionaries and market state
            self.inventory = save_data.get("inventory", self.inventory)
            self.average_cost = save_data.get("average_cost", self.average_cost)
            self.artifact_stock = save_data.get("artifact_stock", self.artifact_stock)
            self.current_market = save_data.get("current_market", self.current_market)
            self.market_prices = save_data.get("market_prices", self.market_prices)
            self.current_hash = save_data.get("current_hash", self.current_hash)
            self.current_events = save_data.get("current_events", [])

            # 4. FORWARD COMPATIBILITY SWEEP!
            for item in self.active_items + self.artifacts:
                if item not in self.inventory:
                    self.inventory[item] = 0
                    self.average_cost[item] = 0

            self.current_events.append("GAME LOADED SUCCESSFULLY!")
            return True
        except Exception as e:
            print(f"Error loading game: {e}")
            time.sleep(2)
            return False

    def render_dashboard(self):
        """ Handles all the static printing logic for the main dashboard. """
        total_inv_value = sum(self.inventory[item] * self.average_cost[item] for item in self.inventory if self.inventory[item] > 0)
        overall_total = self.money + total_inv_value

        self.clear_screen()
        print("=" * 200)

        print(f"   TRADE TYCOON - Week {self.week}")

        # --- EVENT LOG VIEWPORT MATH ---
        MAX_EVENT_LINES = 5
        total_events = len(self.current_events)

        if total_events > 0:
            max_scroll = max(0, total_events - MAX_EVENT_LINES)

            # Clamp scrolling limits
            if self.event_scroll > max_scroll:
                self.event_scroll = max_scroll
            if self.event_scroll < 0:
                self.event_scroll = 0

            start_idx = max(0, total_events - MAX_EVENT_LINES - self.event_scroll)
            end_idx = start_idx + MAX_EVENT_LINES
            visible_events = self.current_events[start_idx:end_idx]

            if self.event_scroll < max_scroll:
                print(f"   {Colors.GRAY}--- ↑ {max_scroll - self.event_scroll} older events ↑ ---{Colors.RESET}")

            for event in visible_events:
                if event.startswith("BOUGHT") or event.startswith("SOLD") or event.startswith("MULTI-"):
                    print(f"   {Colors.GREEN}( {event} ){Colors.RESET}")
                elif event.startswith("GUILD PERMIT"):
                    print(f"   {Colors.GREEN}( +++ {event} +++ ){Colors.RESET}")
                elif event.startswith("A LEGENDARY") or event.startswith("ARTIFACT") or event.startswith("PRESTIGE"):
                    print(f"   {Colors.MAGENTA}( !!! {event} !!! ){Colors.RESET}")
                elif event.startswith("MARKET UPDATE:"):
                    print(f"   {Colors.RED}( {event} ){Colors.RESET}")
                elif event.startswith("GAME SAVED") or event.startswith("GAME LOADED"):
                    print(f"   {Colors.MAGENTA}( *** {event} *** ){Colors.RESET}")
                else:
                    print(f"   {Colors.YELLOW}( *** {event} *** ){Colors.RESET}")

            if self.event_scroll > 0:
                print(f"   {Colors.GRAY}--- ↓ {self.event_scroll} newer events ↓ ---{Colors.RESET}")

            # --- Scroll indicator moved directly beneath the events ---
            if total_events > MAX_EVENT_LINES:
                print(f"   [{Colors.RED}↑/↓{Colors.RESET}] {Colors.RED}Scroll Log{Colors.RESET}")

        print("=" * 200)

        print(f" Current Money: {Colors.YELLOW}${self.money:,}{Colors.RESET}    ||    Inventory Value: ${total_inv_value:,}    ||    Total Value: ${overall_total:,}    ||    Current Score: {self.total_score:,}")

        print("=" * 200)

        # --- DISPLAY LIST SEPARATION ---
        all_visible = list(set(self.active_items + [item for item, qty in self.inventory.items() if qty > 0] + self.current_market))

        # Sort artifacts and normal items into separate lists
        artifact_display = sorted([item for item in all_visible if item in self.artifacts])
        normal_display = sorted([item for item in all_visible if item not in self.artifacts])

        # Master list that numerical input will reference exactly in order
        self.display_items = artifact_display + normal_display

        def format_combined(idx, item):
            qty = self.inventory.get(item, 0)
            avg = self.average_cost.get(item, 0)

            if item in self.market_prices:
                m_price = self.market_prices[item]
                mkt_str = f"[Market: ${m_price:,}]"

                if item in self.artifacts:
                    mkt_color = Colors.MAGENTA
                    if qty > 0:
                        inv_color = Colors.MAGENTA
                        idx_color = Colors.MAGENTA
                    else:
                        inv_color = Colors.GRAY
                        idx_color = Colors.RESET
                else:
                    mkt_color = self.get_price_color(m_price)
                    if qty > 0:
                        inv_color = self.get_price_color(avg)
                        idx_color = inv_color
                    else:
                        inv_color = Colors.GRAY
                        idx_color = Colors.RESET
            else:
                mkt_color = Colors.GRAY
                mkt_str = "[Market: N/A]"

                if item in self.artifacts:
                    inv_color = Colors.MAGENTA
                    idx_color = Colors.MAGENTA
                else:
                    inv_color = Colors.GRAY
                    idx_color = Colors.GRAY

            raw_inv_str = f"[{idx + 1:<2}] {item}: ({qty:,} @ ${avg:,})"
            visible_text = f"{raw_inv_str} --- {mkt_str}"
            visible_len = len(visible_text)

            padding = " " * max(0, 95 - visible_len) # <-- Controls the space between the columns

            colored_inv_str = f"{idx_color}[{idx + 1:<2}]{Colors.RESET} {inv_color}{item}: ({qty:,} @ ${avg:,}){Colors.RESET}"
            return f"{colored_inv_str} {Colors.GRAY}---{Colors.RESET} {mkt_color}{mkt_str}{Colors.RESET}{padding}"

        # --- ARTIFACT PINNED DISPLAY ---
        if artifact_display:
            print(f" {Colors.MAGENTA}*** LEGENDARY ARTIFACTS ***{Colors.RESET}")
            self.print_2_columns(artifact_display, format_combined, start_idx=0)
            print("-" * 200)

        # --- PAGINATION MATH ---
        total_items = len(normal_display)
        items_per_page = 30
        self.total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        # Safety clamp
        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)
        if self.current_page < 0:
            self.current_page = 0

        start_idx = self.current_page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = normal_display[start_idx:end_idx]


        # Normal item index picks up exactly where the artifacts left off
        normal_start_absolute = len(artifact_display) + start_idx
        self.print_2_columns(page_items, format_combined, start_idx=normal_start_absolute)

        page_nav = f" || [{Colors.RED}←{Colors.RESET}] PREV/NEXT [{Colors.RED}→{Colors.RESET}] {Colors.RED}Prev/Next Page{Colors.RESET}" if self.total_pages > 1 else ""
        print(f"\n                                                                                                     (Page {self.current_page + 1} of {self.total_pages}){page_nav}")

        print("=" * 200)

        if self.locked_items:
            cost_text = f"{Colors.RED}${self.unlock_cost:,}{Colors.RESET}" if self.money >= self.unlock_cost else f"${self.unlock_cost:,}"
            score_text = f"{Colors.RED}Score{Colors.RESET}" if self.total_score >= self.unlock_cost else "Score"
            unlock_prompt = f"[{Colors.YELLOW}U{Colors.RESET}]nlock Item ({len(self.locked_items)} Left) ({cost_text} / {score_text})"
        else:
            unlock_prompt = f"{Colors.MAGENTA}*** YOU WON! Everything Is Unlocked! [{Colors.YELLOW}P{Colors.MAGENTA}]restige? ***{Colors.RESET}"

        # --- UPDATED DYNAMIC PROMPT MENU ---
        buy_color = Colors.YELLOW if self.buys_remaining > 0 else Colors.GRAY
        sell_color = Colors.YELLOW if self.sells_remaining > 0 else Colors.GRAY
        
        print(f"Actions: [{buy_color}B{Colors.RESET}]uy ({self.buys_remaining}) | [{sell_color}S{Colors.RESET}]ell/Use ({self.sells_remaining}) | Next [{Colors.YELLOW}W{Colors.RESET}]eek | {unlock_prompt} | [{Colors.YELLOW}F{Colors.RESET}]ile Save | File [{Colors.YELLOW}L{Colors.RESET}]oad | [{Colors.YELLOW}Q{Colors.RESET}]uit")

    def interactive_input(self, prompt_text, custom_renderer=None):
        """ A completely custom input engine that allows screen redrawing during typing! """
        buffer = ""
        while True:
            # If we pass a custom menu, draw that instead of the standard dashboard
            if custom_renderer:
                custom_renderer()
            else:
                self.render_dashboard()

            print(f"{prompt_text}{buffer}", end="", flush=True)

            key = self.get_keypress()

            if key == 'enter':
                print()
                return buffer.strip()
            elif key == 'backspace':
                buffer = buffer[:-1]
            elif key == 'left':
                # Disable main dashboard pagination if we are in a custom menu
                if not custom_renderer and self.total_pages > 1:
                    if self.current_page > 0:
                        self.current_page -= 1
                    else:
                        self.current_page = self.total_pages - 1
            elif key == 'right':
                if not custom_renderer and self.total_pages > 1:
                    if self.current_page < self.total_pages - 1:
                        self.current_page += 1
                    else:
                        self.current_page = 0
            elif key == 'up':
                if not custom_renderer:
                    self.event_scroll += 1
            elif key == 'down':
                if not custom_renderer:
                    self.event_scroll = max(0, self.event_scroll - 1)
            elif len(key) == 1:
                buffer += key

    def run(self):
        self.generate_market()

        while True:
            self.render_dashboard()

            print("What would you like to do? ", end="", flush=True)
            action_raw = self.get_keypress()

            # Handle navigational arrow keys globally if pressed at the main menu
            if action_raw in ['left', 'right', 'up', 'down', 'enter', 'backspace', '']:
                if action_raw == 'up':
                    self.event_scroll += 1
                elif action_raw == 'down':
                    self.event_scroll = max(0, self.event_scroll - 1)
                elif action_raw == 'left':
                    if self.total_pages > 1:
                        if self.current_page > 0: self.current_page -= 1
                        else: self.current_page = self.total_pages - 1
                elif action_raw == 'right':
                    if self.total_pages > 1:
                        if self.current_page < self.total_pages - 1: self.current_page += 1
                        else: self.current_page = 0
                print()
                continue # Redraw the screen immediately

            # Since action_raw wasn't a special key, convert to lower case logic
            action = action_raw.lower()
            print(action.upper())
            self.event_scroll = 0 # Auto-snap to bottom on new action

            if action == 'b':
                if self.buys_remaining <= 0:
                    print("You have exhausted your Buy actions for this week! Advance to the next week, or use an Artifact/Unlock to gain more.")
                    time.sleep(2)
                    continue

                item_input = self.interactive_input(f"Enter item number(s) to buy, or [E]asy Mode: ").strip().lower()
                if not item_input: continue

                is_multi = False
                valid_items = []
                item_idx = -1

                if item_input == 'e':
                    # EASY MODE: Select items not owned OR where market price < average cost
                    valid_items = [
                        item for item in self.display_items 
                        if item not in self.artifacts 
                        and item in self.market_prices 
                        and (self.inventory.get(item, 0) == 0 or self.market_prices[item] < self.average_cost.get(item, 0))
                    ]
                    if not valid_items:
                        print("Easy Mode found no deals (no items are cheaper than your average cost or unowned).")
                        time.sleep(2)
                        continue
                    is_multi = True
                else:
                    try:
                        indices = [int(x.strip()) - 1 for x in item_input.split(',') if x.strip().isdigit()]
                    except ValueError:
                        print("Invalid input format.")
                        time.sleep(1)
                        continue

                    if not indices:
                        continue

                    if len(indices) == 1:
                        item_idx = indices[0]
                        is_multi = False
                    else:
                        valid_items = [self.display_items[i] for i in indices if 0 <= i < len(self.display_items) and self.display_items[i] not in self.artifacts]
                        if not valid_items:
                            print("No valid regular items selected (Note: Artifacts are excluded from multi-trade).")
                            time.sleep(2)
                            continue
                        is_multi = True

                if not is_multi:
                    # --- SINGLE BUY LOGIC ---
                    if 0 <= item_idx < len(self.display_items):
                        item = self.display_items[item_idx]

                        if item not in self.market_prices:
                            print(f"ERROR: {item} is not being traded in the market this week!")
                            time.sleep(1)
                        else:
                            price = self.market_prices[item]
                            max_qty = self.money // price

                            if item in self.artifacts:
                                stock = self.artifact_stock.get(item, 10)
                                if max_qty > stock:
                                    max_qty = stock

                            if max_qty > 0:
                                item_color = Colors.MAGENTA if item in self.artifacts else self.get_price_color(price)
                                input_qty = self.interactive_input(f"How many {item_color}{item}{Colors.RESET} would you like to buy? (Max: {max_qty}, [A]ll/[H]alf/[Q]uarter): ")
                                qty = self.parse_qty(input_qty, max_qty)

                                if 0 < qty <= max_qty:
                                    cost = price * qty
                                    current_qty = self.inventory.get(item, 0)
                                    current_avg = self.average_cost.get(item, 0)
                                    new_qty = current_qty + qty

                                    new_total_value = (current_qty * current_avg) + cost
                                    self.average_cost[item] = new_total_value // new_qty

                                    self.money -= cost
                                    self.inventory[item] = new_qty
                                    self.buys_remaining -= 1
                                    self.current_events.append(f"BOUGHT: {qty:,} {item} for ${cost:,}")

                                    if item in self.artifacts:
                                        self.artifact_stock[item] -= qty
                                        if self.artifact_stock[item] <= 0:
                                            self.current_market.remove(item)
                                            del self.market_prices[item]
                                            self.current_events.append(f"MARKET UPDATE: The market has sold out of {item} for this week!")
                                else:
                                    print("Invalid quantity or not enough money!")
                                    time.sleep(1)
                            else:
                                if item in self.artifacts and self.artifact_stock.get(item, 10) <= 0:
                                    print(f"The market is sold out of {item}!")
                                else:
                                    print(f"You can't even afford one {item}!")
                                time.sleep(1)
                    else:
                        print("Invalid item number!")
                        time.sleep(1)

                else:
                    # --- MULTI BUY LOGIC ---
                    prompt_prefix = f"Easy Mode selected {len(valid_items)} items! " if item_input == 'e' else ""
                    amount_input = self.interactive_input(f"{prompt_prefix}How much of your budget do you want to spend? ([A]ll / [H]alf / [Q]uarter): ").strip().lower()
                    
                    if amount_input in ['a', 'all']: fraction = 1.0
                    elif amount_input in ['h', 'half']: fraction = 0.5
                    elif amount_input in ['q', 'quarter']: fraction = 0.25
                    else:
                        print("Invalid amount.")
                        time.sleep(1)
                        continue

                    buyable_items = [item for item in valid_items if item in self.market_prices]
                    
                    if buyable_items:
                        total_budget = int(self.money * fraction)
                        budget_per_item = total_budget // len(buyable_items)
                        
                        total_trades = 0
                        total_value = 0
                        trade_details = []

                        for item in buyable_items:
                            price = self.market_prices[item]
                            qty = budget_per_item // price
                            
                            if qty > 0:
                                cost = price * qty
                                current_qty = self.inventory.get(item, 0)
                                current_avg = self.average_cost.get(item, 0)
                                new_qty = current_qty + qty
                                
                                new_total_value = (current_qty * current_avg) + cost
                                self.average_cost[item] = new_total_value // new_qty
                                
                                self.money -= cost
                                self.inventory[item] = new_qty
                                
                                total_trades += 1
                                total_value += cost
                                trade_details.append(f"{qty:,}x {item}")

                        if total_trades > 0:
                            details_str = ", ".join(trade_details)
                            self.buys_remaining -= 1
                            self.current_events.append(f"MULTI-BUY: Bought ({details_str}) for a total of ${total_value:,}!")
                        else:
                            print("Your allocated budget per item isn't enough to afford the selected goods.")
                            time.sleep(2)
                    else:
                        print("None of those selected items are currently available in the market.")
                        time.sleep(2)

            elif action == 's':
                item_input = self.interactive_input(f"Enter item number(s) to sell/use, or [E]asy Mode: ").strip().lower()
                if not item_input: continue

                is_multi = False
                valid_items = []
                item_idx = -1

                if item_input == 'e':
                    # EASY MODE: Select items where owned > 0 AND market price > average cost
                    valid_items = [
                        item for item in self.display_items 
                        if item not in self.artifacts 
                        and item in self.market_prices 
                        and self.inventory.get(item, 0) > 0 
                        and self.market_prices[item] > self.average_cost.get(item, 0)
                    ]
                    if not valid_items:
                        print("Easy Mode found no profitable items to sell.")
                        time.sleep(2)
                        continue
                    is_multi = True
                else:
                    try:
                        indices = [int(x.strip()) - 1 for x in item_input.split(',') if x.strip().isdigit()]
                    except ValueError:
                        print("Invalid input format.")
                        time.sleep(1)
                        continue

                    if not indices:
                        continue

                    if len(indices) == 1:
                        item_idx = indices[0]
                        is_multi = False
                    else:
                        valid_items = [self.display_items[i] for i in indices if 0 <= i < len(self.display_items) and self.display_items[i] not in self.artifacts]
                        if not valid_items:
                            print("No valid regular items selected (Note: Artifacts are excluded from multi-trade).")
                            time.sleep(2)
                            continue
                        is_multi = True

                if not is_multi:
                    # --- SINGLE SELL/USE LOGIC ---
                    if 0 <= item_idx < len(self.display_items):
                        item = self.display_items[item_idx]

                        if item in self.artifacts:
                            if self.inventory.get(item, 0) > 0:
                                
                                # Build the multiline prompt string
                                power_desc = ""
                                if item == "Smuggler's Writ":
                                    power_desc = "POWER: Bypass local tariffs and force the market to accept ANY item from your inventory!"
                                elif item == "Black Swan Catalyst":
                                    power_desc = "POWER: Triggers a geopolitical crisis! (Crashes 1/4 of the market commodities, skyrockets another 1/4)"
                                elif item == "Political Favors":
                                    power_desc = "POWER: Call in a massive favor from the Crown! Instantly receive 10,000 of ANY item (even locked ones) for free!"
                                elif item == "Owl-Chemist":
                                    power_desc = "POWER: Convert any existing item into any other known item at a 1:1 ratio!"

                                artifact_prompt = f"\n{Colors.MAGENTA}*** ARTIFACT SELECTED: {item} ***{Colors.RESET}\n{power_desc}\nDo you want to invoke this artifact? (Y/N): "
                                
                                # Use interactive input so arrow keys still work!
                                confirm = self.interactive_input(artifact_prompt).strip().lower()
                                
                                if confirm == 'y':
                                    if item == "Smuggler's Writ":
                                        try:
                                            smuggle_idx_str = self.interactive_input(f"Enter the dashboard number of the item you want to smuggle: ")
                                            smuggle_idx = int(smuggle_idx_str) - 1
                                            if 0 <= smuggle_idx < len(self.display_items):
                                                smuggle_item = self.display_items[smuggle_idx]
                                                max_qty = self.inventory.get(smuggle_item, 0)

                                                if max_qty > 0 and smuggle_item not in self.artifacts:
                                                    sell_price = self.average_cost.get(smuggle_item, 1)
                                                    if sell_price <= 0:
                                                        sell_price = 1

                                                    smuggle_color = Colors.MAGENTA if smuggle_item in self.artifacts else self.get_price_color(sell_price)
                                                    input_qty = self.interactive_input(f"How many {smuggle_color}{smuggle_item}{Colors.RESET} would you like to smuggle? (Max: {max_qty}, [A]ll/[H]alf/[Q]uarter): ")
                                                    qty = self.parse_qty(input_qty, max_qty)

                                                    if 0 < qty <= max_qty:
                                                        self.inventory[item] -= 1
                                                        if self.inventory[item] == 0:
                                                            self.average_cost[item] = 0

                                                        revenue = sell_price * qty
                                                        self.money += revenue
                                                        self.total_score += revenue
                                                        self.inventory[smuggle_item] -= qty

                                                        if self.inventory[smuggle_item] == 0:
                                                            self.average_cost[smuggle_item] = 0

                                                        self.buys_remaining += 1
                                                        self.sells_remaining += 1

                                                        if smuggle_item not in self.market_prices:
                                                            self.current_market.append(smuggle_item)
                                                            self.market_prices[smuggle_item] = sell_price
                                                            self.current_market.sort()
                                                            self.sync_artifact_prices()
                                                            self.current_events.append(f"ARTIFACT INVOKED: Sold {qty:,} {smuggle_item} for ${revenue:,}. The market now accepts {smuggle_item}! (+1 Buy/Sell Action Granted!)")
                                                        else:
                                                            self.current_events.append(f"ARTIFACT INVOKED: Sold {qty:,} {smuggle_item} for ${revenue:,}. (+1 Buy/Sell Action Granted!)")
                                                    else:
                                                        print("Invalid quantity. Invocation cancelled.")
                                                        time.sleep(1)
                                                else:
                                                    print("You cannot smuggle that item. Invocation cancelled.")
                                                    time.sleep(1)
                                            else:
                                                print("Invalid item number. Invocation cancelled.")
                                                time.sleep(1)
                                        except ValueError:
                                            print("Invalid input. Invocation cancelled.")
                                            time.sleep(1)

                                    elif item == "Black Swan Catalyst":
                                        self.inventory[item] -= 1
                                        if self.inventory[item] == 0:
                                            self.average_cost[item] = 0

                                        targets = [m for m in self.current_market if m not in self.artifacts]
                                        impact_qty = len(targets) // 2

                                        if impact_qty < 1 and len(targets) >= 2:
                                            impact_qty = 1

                                        if impact_qty >= 1 and len(targets) >= (impact_qty * 2):
                                            affected = random.sample(targets, impact_qty * 2)
                                            moons = affected[:impact_qty]
                                            crashes = affected[impact_qty:]

                                            for moon in moons:
                                                multiplier = random.randint(25, 50)
                                                baseline = 100 + (self.unlocked_count * 10)
                                                self.market_prices[moon] = (self.market_prices[moon] * multiplier) + baseline

                                            for crash in crashes:
                                                self.market_prices[crash] = 1

                                            self.sync_artifact_prices()

                                            self.buys_remaining += 1
                                            self.sells_remaining += 1

                                            moon_str = ", ".join(moons)
                                            crash_str = ", ".join(crashes)

                                            self.current_events.append(f"ARTIFACT INVOKED: {item} (+1 Buy/Sell Action Granted!)")
                                        else:
                                            self.current_events.append(f"ARTIFACT INVOKED: {item} - The market was too small for a crisis.")

                                    elif item == "Political Favors":
                                        all_possible = sorted(self.active_items + self.locked_items)
                                        
                                        def render_armory():
                                            self.clear_screen()
                                            print("=" * 200)
                                            print(f"   {Colors.MAGENTA}*** ROYAL ARMORY (Political Favors) ***{Colors.RESET}")
                                            print("=" * 200)

                                            def format_armory(idx, it):
                                                return f"[{idx + 1:<2}] {it:<45}"

                                            self.print_3_columns(all_possible, format_armory)
                                            print("=" * 200)

                                        try:
                                            # Using the custom_renderer prevents the main dashboard from wiping our cool menu!
                                            fav_idx = int(self.interactive_input(f"Enter the number of the item you want 10,000 of (1-{len(all_possible)}): ", custom_renderer=render_armory)) - 1
                                            if 0 <= fav_idx < len(all_possible):
                                                target_item = all_possible[fav_idx]

                                                self.inventory[item] -= 1
                                                if self.inventory[item] == 0:
                                                    self.average_cost[item] = 0

                                                if target_item not in self.inventory:
                                                    self.inventory[target_item] = 0
                                                    self.average_cost[target_item] = 0

                                                current_qty = self.inventory.get(target_item, 0)
                                                new_qty = current_qty + 10000
                                                self.inventory[target_item] = new_qty
                                                
                                                self.buys_remaining += 1
                                                self.sells_remaining += 1

                                                self.current_events.append(f"ARTIFACT INVOKED: Political Favors - The Crown granted you 10,000 {target_item}! (+1 Buy/Sell Action Granted!)")
                                            else:
                                                print("Invalid selection. Invocation cancelled.")
                                                time.sleep(1)
                                        except ValueError:
                                            print("Invalid input. Invocation cancelled.")
                                            time.sleep(1)

                                    elif item == "Owl-Chemist":
                                        try:
                                            source_idx_str = self.interactive_input(f"Enter the dashboard number of the item you want to convert FROM: ")
                                            source_idx = int(source_idx_str) - 1
                                            if 0 <= source_idx < len(self.display_items):
                                                source_item = self.display_items[source_idx]
                                                max_qty = self.inventory.get(source_item, 0)

                                                if max_qty > 0 and source_item not in self.artifacts:
                                                    source_price = self.market_prices.get(source_item, 1)
                                                    source_color = self.get_price_color(source_price)

                                                    input_qty = self.interactive_input(f"How many {source_color}{source_item}{Colors.RESET} would you like to convert? (Max: {max_qty}, [A]ll/[H]alf/[Q]uarter): ")
                                                    qty = self.parse_qty(input_qty, max_qty)

                                                    if 0 < qty <= max_qty:
                                                        all_possible = sorted(self.active_items + self.locked_items)
                                                        
                                                        def render_alchemy():
                                                            self.clear_screen()
                                                            print("=" * 200)
                                                            print(f"   {Colors.MAGENTA}*** ALCHEMY LAB (Owl-Chemist) ***{Colors.RESET}")
                                                            print("=" * 200)

                                                            def format_alchemy(idx, it):
                                                                return f"[{idx + 1:<2}] {it:<45}"

                                                            self.print_3_columns(all_possible, format_alchemy)
                                                            print("=" * 200)

                                                        try:
                                                            target_idx = int(self.interactive_input(f"Enter the number of the item you want to convert INTO (1-{len(all_possible)}): ", custom_renderer=render_alchemy)) - 1
                                                            if 0 <= target_idx < len(all_possible):
                                                                target_item = all_possible[target_idx]

                                                                if source_item == target_item:
                                                                    print("You cannot convert an item into itself!")
                                                                    time.sleep(1)
                                                                else:
                                                                    self.inventory[item] -= 1
                                                                    if self.inventory[item] == 0:
                                                                        self.average_cost[item] = 0

                                                                    self.inventory[source_item] -= qty
                                                                    if self.inventory[source_item] == 0:
                                                                        self.average_cost[source_item] = 0

                                                                    if target_item not in self.inventory:
                                                                        self.inventory[target_item] = 0
                                                                        self.average_cost[target_item] = 0

                                                                    current_target_qty = self.inventory.get(target_item, 0)
                                                                    new_target_qty = current_target_qty + qty
                                                                    self.inventory[target_item] = new_target_qty
                                                                    
                                                                    self.buys_remaining += 1
                                                                    self.sells_remaining += 1

                                                                    self.current_events.append(f"ARTIFACT INVOKED: Owl-Chemist - Converted {qty:,} {source_item} into {target_item}! (+1 Buy/Sell Action Granted!)")
                                                            else:
                                                                print("Invalid selection. Invocation cancelled.")
                                                                time.sleep(1)
                                                        except ValueError:
                                                            print("Invalid input. Invocation cancelled.")
                                                            time.sleep(1)
                                                    else:
                                                        print("Invalid quantity. Invocation cancelled.")
                                                        time.sleep(1)
                                                else:
                                                    print("You cannot convert that item. Invocation cancelled.")
                                                    time.sleep(1)
                                            else:
                                                print("Invalid item number. Invocation cancelled.")
                                                time.sleep(1)
                                        except ValueError:
                                            print("Invalid input. Invocation cancelled.")
                                            time.sleep(1)
                                else:
                                    print("Artifact invocation cancelled.")
                                    time.sleep(1)
                            else:
                                print(f"You don't possess a {item} to use!")
                                time.sleep(1)

                        else:
                            # Not an artifact, verify standard sell actions
                            if self.sells_remaining <= 0:
                                print("You have exhausted your Sell actions for this week! Advance to the next week, or use an Artifact/Unlock to gain more.")
                                time.sleep(2)
                                continue

                            if item not in self.market_prices:
                                print(f"ERROR: No merchants are buying {item} this week!")
                                time.sleep(1)
                            else:
                                price = self.market_prices[item]
                                max_qty = self.inventory.get(item, 0)

                                if max_qty > 0:
                                    item_color = self.get_price_color(price)
                                    input_qty = self.interactive_input(f"How many {item_color}{item}{Colors.RESET} would you like to sell? (Max: {max_qty}, [A]ll/[H]alf/[Q]uarter): ")
                                    qty = self.parse_qty(input_qty, max_qty)

                                    if 0 < qty <= max_qty:
                                        revenue = price * qty
                                        self.money += revenue
                                        self.total_score += revenue
                                        self.inventory[item] -= qty

                                        if self.inventory[item] == 0:
                                            self.average_cost[item] = 0

                                        self.sells_remaining -= 1
                                        self.current_events.append(f"SOLD: {qty:,} {item} for ${revenue:,}")
                                    else:
                                        print(f"Invalid quantity or you don't have that many {item}!")
                                        time.sleep(1)
                                else:
                                    print(f"You don't have any {item} to sell!")
                                    time.sleep(1)
                    else:
                        print("Invalid item number!")
                        time.sleep(1)

                else:
                    # --- MULTI SELL LOGIC ---
                    if self.sells_remaining <= 0:
                        print("You have exhausted your Sell actions for this week! Advance to the next week, or use an Artifact/Unlock to gain more.")
                        time.sleep(2)
                        continue

                    prompt_prefix = f"Easy Mode found {len(valid_items)} profitable items! " if item_input == 'e' else ""
                    amount_input = self.interactive_input(f"{prompt_prefix}How much of each item do you want to sell? ([A]ll / [H]alf / [Q]uarter): ").strip().lower()
                    
                    if amount_input in ['a', 'all']: fraction = 1.0
                    elif amount_input in ['h', 'half']: fraction = 0.5
                    elif amount_input in ['q', 'quarter']: fraction = 0.25
                    else:
                        print("Invalid amount.")
                        time.sleep(1)
                        continue

                    total_trades = 0
                    total_value = 0
                    trade_details = []

                    for item in valid_items:
                        if item in self.market_prices:
                            max_qty = self.inventory.get(item, 0)
                            qty = int(max_qty * fraction)
                            if qty > 0:
                                price = self.market_prices[item]
                                revenue = price * qty
                                self.money += revenue
                                self.total_score += revenue
                                self.inventory[item] -= qty
                                if self.inventory[item] == 0:
                                    self.average_cost[item] = 0
                                
                                total_trades += 1
                                total_value += revenue
                                trade_details.append(f"{qty:,}x {item}")
                                
                    if total_trades > 0:
                        details_str = ", ".join(trade_details)
                        self.sells_remaining -= 1
                        self.current_events.append(f"MULTI-SELL: Sold ({details_str}) for a total of ${total_value:,}!")
                    else:
                        print("You do not have enough inventory of those items to sell.")
                        time.sleep(1)

            elif action == 'w':
                self.week += 1
                self.buys_remaining = 1
                self.sells_remaining = 1
                self.generate_market()
                self.trigger_event()

            elif action == 'u':
                if self.locked_items:
                    can_unlock = False
                    paid_with = ""

                    if self.money >= self.unlock_cost:
                        self.money -= self.unlock_cost
                        can_unlock = True
                        paid_with = "Money"
                    elif self.total_score >= self.unlock_cost:
                        self.total_score -= self.unlock_cost
                        can_unlock = True
                        paid_with = "Score"

                    if can_unlock:
                        # --- NEW RANDOM UNLOCK LOGIC ---
                        unlock_hex = self.current_hash[-2:]
                        unlock_val = int(unlock_hex, 16)
                        unlock_index = unlock_val % len(self.locked_items)

                        new_item = self.locked_items.pop(unlock_index)
                        self.active_items.append(new_item)

                        if new_item not in self.inventory:
                            self.inventory[new_item] = 0
                            self.average_cost[new_item] = 0

                        self.unlocked_count += 1
                        self.unlock_cost = int(self.unlock_cost * 1.25)
                        self.current_market.append(new_item)

                        total_artifacts = sum(self.inventory.get(art, 0) for art in self.artifacts)
                        seed_string = f"run_{self.run_id}_money_{self.money}_score_{self.total_score}_unlocked_{self.unlocked_count}_arts_{total_artifacts}_week_{self.week}"
                        seed_string_two = f"run_{self.run_id}_week_{self.week}_score_{self.total_score}_unlocked_{self.unlocked_count}_money_{self.money}"

                        market_hash = self.get_market_hash(seed_string, seed_string_two)
                        self.current_hash = market_hash

                        for i, m_item in enumerate(self.current_market):
                            if m_item in self.artifacts:
                                continue
                            hex_pair = market_hash[i*2 : (i*2)+2]
                            raw_hash_price = int(hex_pair, 16)
                            scaling_bonus = self.unlocked_count * 5
                            self.market_prices[m_item] = max(1, raw_hash_price + scaling_bonus)

                        self.current_market.sort()
                        self.sync_artifact_prices()
                        
                        self.buys_remaining += 1
                        self.sells_remaining += 1
                        
                        self.current_events.append(f"GUILD PERMIT SECURED: {new_item} (Paid with {paid_with}). The market fluctuates immediately! (+1 Buy/Sell Action Granted!)")
                    else:
                        print(f"You need ${self.unlock_cost:,} or Score to unlock a new item!")
                        time.sleep(2)
                else:
                    print("You have already unlocked all the realm's items!")
                    time.sleep(2)

            elif action == 'f':
                self.save_game()

            elif action == 'l':
                if os.path.exists(self.save_file):
                    confirm = self.interactive_input("\n Are you sure you want to load? Any unsaved progress will be lost! (Y/N): ").strip().lower()
                    if confirm == 'y':
                        self.load_game()
                    else:
                        print(" Load cancelled.")
                        time.sleep(1)
                else:
                    print(" No save file found!")
                    time.sleep(1)

            elif action == 'p':
                if not self.locked_items:
                    bonus_gp = int(self.total_score ** (1/4.0))

                    prestige_prompt = (
                        f"\n{Colors.MAGENTA}*** PRESTIGE ***{Colors.RESET}\n"
                        f" You have cornered the market and unlocked every good in the realm!\n"
                        f" If you Prestige, your empire will reset, but you will retain the following perks:\n"
                        f"   - {Colors.YELLOW}Extra Starting Wealth:{Colors.RESET} +${bonus_gp:,} (Bonus from getting a high score of {self.total_score:,})\n"
                        f"   - {Colors.MAGENTA}Legendary Heirloom:{Colors.RESET} Keep your entire collected stack of 1 Artifact type (minimum 1)\n\n"
                        f" Are you ready to pass the torch to the next generation? (Y/N): "
                    )

                    confirm = self.interactive_input(prestige_prompt).strip().lower()
                    
                    if confirm == 'y':
                        art_prompt = "\n Which artifact would you like to keep?\n"
                        for idx, art in enumerate(self.artifacts):
                            art_prompt += f" [{idx + 1}] {art}\n"
                        art_prompt += " Enter number (1-4): "

                        try:
                            art_choice = int(self.interactive_input(art_prompt)) - 1
                            if 0 <= art_choice < len(self.artifacts):
                                chosen_art = self.artifacts[art_choice]
                            else:
                                print(" Invalid selection. The Guild assigns you a Smuggler's Writ.")
                                chosen_art = self.artifacts[0]
                                time.sleep(1)
                        except ValueError:
                            print(" Invalid input. The Guild assigns you a Smuggler's Writ.")
                            chosen_art = self.artifacts[0]
                            time.sleep(1)

                        kept_qty = max(1, self.inventory.get(chosen_art, 0))

                        # --- RESET THE GAME STATE USING THE NEW HELPER FUNCTION ---
                        self.reset_game_state(bonus_gp=bonus_gp, kept_artifact=chosen_art, kept_qty=kept_qty)

                        self.generate_market()
                        self.current_events = [f"PRESTIGE SECURED! You start anew with an extra ${bonus_gp:,} and {kept_qty:,}x {chosen_art}."]

                    else:
                        print(" Prestige cancelled.")
                        time.sleep(1)
                else:
                    print(" ERROR: You must unlock every item in the realm before you can Prestige!")
                    time.sleep(2)

            elif action == 'q':
                print(f"\nSafe travels, Tycoon! Your score for this game was {self.total_score:,}\n")
                break

            else:
                print("Invalid option.")
                time.sleep(1)

if __name__ == "__main__":
    game = TradeTycoon()
    game.run()