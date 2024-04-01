#
#    To get this to work you must change login information in the following lines:
#
#    SolarWinds login in lines 75-77, 85-87 and 312-315
#    SWICH Username/Passwords in lines: 141, 333, 497
#

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.uix.image import Image
from orionsdk import SwisClient
from kivy.uix.textinput import TextInput
import paramiko

selected_switch_info = None

exclude_strings = ["arubamc", "arubamm"] #excludes solarwinds names to not break core equipment


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.switch_options = self.get_switch_options()  # Populate switch options
        self.switch_info = {}  # Dictionary to store switch info
        self.populate_switch_info_menu()  # Corrected method name

        # Create a BoxLayout for the menu screen
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)

        # Add title label
        title_label = Label(text='Switch Interface', font_size=40, size_hint=(None, None), size=(400, 70),
                            pos_hint={'center_x': 0.5})
        layout.add_widget(title_label)

        # Add subtitle label
        subtitle_label = Label(text='Select a switch:', font_size=24, size_hint=(None, None), size=(400, 40),
                               pos_hint={'center_x': 0.5})
        layout.add_widget(subtitle_label)

        # Add search bar
        self.search_bar = TextInput(hint_text='Search...', multiline=False, size_hint=(None, None), size=(400, 50),
                                     pos_hint={'center_x': 0.5})
        self.search_bar.bind(text=self.on_search_text)
        layout.add_widget(self.search_bar)

        # Add switch menu (spinner)
        self.switch_menu = Spinner(text='Select Switch', values=self.switch_options, font_size=18,
                                   size_hint=(None, None), size=(400, 50), pos_hint={'center_x': 0.5})
        self.switch_menu.bind(text=self.on_switch_selected)
        layout.add_widget(self.switch_menu)

        # Add switch info label
        self.switch_info_label = Label(text='', font_size=18, size_hint=(None, None), size=(400, 50),
                                       pos_hint={'center_x': 0.5})
        layout.add_widget(self.switch_info_label)

        # Add an open connection button
        open_connection_button = Button(text='Open Connection', font_size=18, size_hint=(None, None), size=(400, 50),
                                        pos_hint={'center_x': 0.5})
        open_connection_button.bind(on_release=self.open_connection)
        layout.add_widget(open_connection_button)

        # Add the layout to the screen
        self.add_widget(layout)

    def get_switch_options(self):
        # SolarWinds connection details
        hostname = 'SOLARWINDS IP GOES HERE'
        username = 'SOLARWINDS USERNAME GOES HERE'
        password = 'SOLARWINDS PASSWORD GOES HERE'
        vendors = ['Aruba Networks Inc']  # Filter by vendor if needed

        # Call function to connect to SolarWinds and retrieve switch information
        switches = self.connect_to_solarwinds(hostname, username, password, vendors, exclude_strings)
        return [switch['SwitchName'] for switch in switches]

    def populate_switch_info_menu(self):
        hostname = 'SOLARWINDS IP GOES HERE'
        username = 'SOLARWINDS USERNAME GOES HERE'
        password = 'SOLARWINDS PASSWORD GOES HERE'
        vendors = ['Aruba Networks Inc']  # Filter by vendor if needed

        # Call function to connect to SolarWinds and retrieve switch information
        switches = self.connect_to_solarwinds(hostname, username, password, vendors, exclude_strings)
        self.switch_info = {switch['SwitchName']: {
            'SwitchName': switch['SwitchName'],
            'IPAddress': switch['IPAddress'],  # Ensure 'IPAddress' key is included
            'VendorType': switch['VendorType']
        } for switch in switches}


    def on_switch_selected(self, instance, text):
        global selected_switch_info  # Use global variable
        selected_switch_info = self.switch_info[text]  # Store selected switch info
        switch_info = selected_switch_info


    def connect_to_solarwinds(self, hostname, username, password, vendors, exclude_strings):
        switches = []
        swis = SwisClient(hostname, username, password)
        query = """
        SELECT N.SysName AS SwitchName, N.IPAddress AS IPAddress, N.Vendor AS VendorType
        FROM Orion.Nodes N
        WHERE N.Vendor IN @vendors
        """
        for i, exclude_string in enumerate(exclude_strings):
            query += "AND NOT (N.SysName LIKE '%' + @exclude_string{} + '%')".format(i)
        query += "ORDER BY N.Vendor, N.SysName"
        parameters = {'vendors': vendors}
        for i, exclude_string in enumerate(exclude_strings):
            parameters['exclude_string{}'.format(i)] = exclude_string
        results = swis.query(query, **parameters)
        for row in results['results']:
            switches.append({
                'SwitchName': row['SwitchName'],
                'IPAddress': row['IPAddress'],
                'VendorType': row['VendorType']
            })
        return switches




    def on_search_text(self, instance, value):
        filtered_options = [option for option in self.switch_options if value.lower() in option.lower()]
        self.switch_menu.values = filtered_options


    def open_connection(self, instance):
        selected_switch = self.switch_menu.text
        selected_info = self.switch_info[selected_switch]

        # SSH into the switch and get VSF output
        output = ssh_into_switch(selected_info['IPAddress'], 'SWITCH USERNAME', 'SWITCH PASSWORD', 'sh vsf')

        # Parse VSF output
        if output:
            #print(output)
            num_ids = parse_vsf_output(output)
            if num_ids is not None:
                # Limit the increment switch variable based on the number of switches
                SwitchGUI.max_switch_number = num_ids

                # Switch to the switch GUI screen and pass the selected info
                self.manager.current = 'switch_gui'
                switch_gui_screen = self.manager.get_screen('switch_gui')
                switch_gui_screen.update_info(selected_info)
                switch_gui_screen.update_switch_info()  # Update switch info for SwitchGUI

                return

        # Display an error message if SSH or parsing fails
        popup_content = Label(text="Failed to retrieve switch information.")
        popup = Popup(title="Error", content=popup_content, size_hint=(None, None), size=(300, 200))
        popup.open()





def ssh_into_switch(hostname, username, password, command):
    # Initialize SSH client
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the switch
        ssh_client.connect(hostname=hostname, username=username, password=password, timeout=10)

        # Execute the command
        stdin, stdout, stderr = ssh_client.exec_command(command)

        # Read the output
        output = stdout.read().decode('utf-8')

        # Close the SSH connection
        ssh_client.close()

        return output

    except Exception as e:
        print("An error occurred:", str(e))
        return None

def parse_vsf_output(output):
    # Split the output into lines
    lines = output.strip().split('\n')

    # Find the index of the "ID" line
    id_index = lines.index('ID')

    # Count the number of lines that contain a numerical ID
    num_ids = sum(1 for line in lines[id_index + 1:] if line.strip().split()[0].isdigit())

    print("Number of IDs:", num_ids)
    return num_ids

class SwitchButton(Button):
    def __init__(self, port_number, **kwargs):
        super().__init__(**kwargs)
        self.port_number = port_number
        self.interface_config = None

    def on_press(self):
        # Check if interface_config is available
        if self.interface_config:
            # Create popup with port configuration
            popup_content = Label(text=self.interface_config)
            popup = Popup(title=f"Port {self.port_number} Configuration", content=popup_content,
                          size_hint=(None, None), size=(400, 400))
            popup.open()
        else:
            # If interface_config is not available, display a message indicating so
            popup_content = Label(text="Port configuration not available.")
            popup = Popup(title=f"Port {self.port_number} Configuration", content=popup_content,
                          size_hint=(None, None), size=(300, 200))
            popup.open()

        # Print the interface_config received
       # print("Interface Config for Port {}: {}".format(self.port_number, self.interface_config))





class SwitchGUI(Screen):
    active_switch = 1  # Variable to keep track of active switch
    max_switch_number = 1
    increment_value = 1

    def on_enter(self):
        # Call ssh_into_selected_switch when the screen is entered
        if selected_switch_info:
            command_output = self.ssh_into_selected_switch()
           # print(command_output)


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.switch_info_label = Label(text='', font_size=18, size_hint=(None, None), size=(400, 50),
                                       pos_hint={'center_x': 0.5, 'top': 0.95})
        self.add_widget(self.switch_info_label)
        self.interfaces_with_zero_counters = set()
        self.ssh_client = None

        switch_panel_image = Image(source='EmptySwitch.png')
        self.add_widget(switch_panel_image)

        show_counters_button = Button(text='Show Counters', font_size=18, size_hint=(None, None), size=(400, 50),
                                      pos_hint={'center_x': 0.5})
        show_counters_button.bind(on_release=self.show_counters)
        self.add_widget(show_counters_button)
        
        # Add Next switch button to the bottom left
        next_switch_button = Button(text='Next Switch', font_size=18, size_hint=(None, None), size=(200, 50),
                                    pos_hint={'left': 0.05, 'y': 0.08})
        next_switch_button.bind(on_release=self.next_switch)
        self.add_widget(next_switch_button)
        
        # Add Previous switch button to the bottom left
        prev_switch_button = Button(text='Previous Switch', font_size=18, size_hint=(None, None), size=(200, 50),
                                    pos_hint={'left': 0.05, 'y': 0.005})
        prev_switch_button.bind(on_release=self.previous_switch)
        self.add_widget(prev_switch_button)
        
        # Add go to home button to the bottom right
        go_to_home_button = Button(text='Go to Home', font_size=18, size_hint=(None, None), size=(200, 50),
                                   pos_hint={'right': 0.95, 'y': 0.05})
        go_to_home_button.bind(on_release=self.go_to_home)
        self.add_widget(go_to_home_button)

    def next_switch(self, instance):
        if self.active_switch < self.max_switch_number:
            self.active_switch += 1
            self.update_switch_info()  # Update switch info
            self.reset_buttons()  # Reset button colors based on the new active switch
            # Re-parse the command output for the new active switch
            self.parse_switch_output()

    def previous_switch(self, instance):
        if self.active_switch > 1:
            self.active_switch -= 1
            self.update_switch_info()  # Update switch info
            self.reset_buttons()  # Reset button colors based on the new active switch
            # Re-parse the command output for the new active switch
            self.parse_switch_output()



    def update_switch_info(self):
        selected_switch = self.manager.get_screen('menu').switch_menu.text
        selected_info = self.manager.get_screen('menu').switch_info[selected_switch]
        self.switch_info_label.text = f"Name: {selected_info.get('SwitchName', '')}\nIP: {selected_info.get('IPAddress', '')}\nVendor: {selected_info.get('VendorType', '')}\nCurrent Switch in Stack: {self.active_switch}"

    def reset_buttons(self):
        # Iterate over all child widgets
        for widget in self.children:
            # Check if the widget is an instance of SwitchButton
            if isinstance(widget, SwitchButton):
                # Reset the background color of the button to the default color
                widget.background_color = [1, 1, 1, 1]  # Default color


    def populate_switch_info_gui(self):
        # SolarWinds connection details
        hostname = 'SOLARWINDS IP GOES HERE'
        username = 'SOLARWINDS USERNAME GOES HERE'
        password = 'SOLARWINDS PASSWORD GOES HERE'
        vendors = ['Aruba Networks Inc']  # Filter by vendor if needed

        # Call function to connect to SolarWinds and retrieve switch information
        switches = self.connect_to_solarwinds(hostname, username, password, vendors, exclude_strings)
        self.switch_info = {switch['SwitchName']: {
            'SwitchName': switch['SwitchName'],
            'IPAddress': switch['IPAddress'],  # Ensure 'IPAddress' key is included
            'VendorType': switch['VendorType']
        } for switch in switches}

    def ssh_into_selected_switch(self):
        global selected_switch_info  # Use global variable
        if selected_switch_info:
            ip_address = selected_switch_info.get('IPAddress')
            #print("SSH into selected switch:", ip_address)  # Print IP address for debugging

            # Run the show command to get switch interface configurations
            switch_output = ssh_into_switch(ip_address, 'SWITCH USERNAME', 'SWITCH PASSWORD', 'show running-config interface | exclude "interface vlan" | exclude "no shutdown" | exclude "no routing" | exclude "exit" | exclude "interface mgmt"')
            
            # Parse the switch output and map configurations to buttons
            if switch_output:
                self.map_port_configs_to_buttons(switch_output)
            else:
                print("Failed to retrieve switch interface configurations.")
        else:
            print("No switch info available.")


    def parse_switch_output(self):
        command_output = self.ssh_into_selected_switch()
        if command_output:
            self.map_port_configs_to_buttons(command_output)
        else:
            print("Failed to retrieve switch interface configurations.")



    def map_port_configs_to_buttons(self, command_output):
        # Clear existing interface configurations
        for child in self.children:
            if isinstance(child, SwitchButton):
                child.interface_config = None

        # Split the output into lines
        lines = command_output.strip().split('\n')

        # Initialize variables
        current_interface = None
        port_config = ''
        switch_prefix = str(self.active_switch) + '/'

        # Iterate over each line and process interface configurations
        for line_index, line in enumerate(lines):
            # Check if the line represents a new interface configuration
            if line.startswith('interface'):
                # Check if the interface belongs to the active switch
                if line.startswith(f'interface {switch_prefix}'):
                    # If it belongs to the active switch, update port_config and current_interface
                    current_interface = line.strip().split()[1]
                    port_config = line + '\n'  # Start with the interface line
                else:
                    # Skip interface configurations not belonging to the active switch
                    current_interface = None
            else:
                # Append lines to port_config until a new interface configuration is encountered
                if current_interface and line.strip():  # Ensure non-empty lines are considered
                    port_config += line + '\n'

                    # If the next line starts with 'interface', it indicates a new interface configuration
                    if line_index + 1 < len(lines) and lines[line_index + 1].startswith('interface'):
                        # Map the interface configuration to the corresponding button
                        button_number = int(current_interface.split('/')[-1])  # Extract port number
                        button = self.get_button_by_port_number(button_number)
                        if button:
                            button.interface_config = port_config  # Set interface config for the button

                        # Reset variables for the next interface configuration
                        current_interface = None
                        port_config = ''







    def get_button_by_port_number(self, port_number):
        # Iterate over child widgets and find the button with the given port number
        for button in self.children:
            if isinstance(button, SwitchButton) and button.port_number == port_number:
              #  print(button)
                return button  # Return the button if found
        return None  # Return None if button not found



    def map_ports_to_buttons(self, output):
        # Split the output into lines
        lines = output.strip().split('\n')

        # Remove header lines and separator lines
        lines = lines[3:]

        # Initialize a set to store interfaces with 0 counters
        zero_counter_interfaces = set()

        # Define the prefix for ports based on the active switch
        port_prefix = str(self.active_switch) + "/"

        # Iterate over each line and map port numbers to buttons
        # Iterate over each line and map port numbers to buttons
        for line in lines:
            # Split the line into columns
            columns = line.split()
            if len(columns) > 0:
                # Extract port number from the first column
                port_number = columns[0]
               # print("Port number:", port_number)  # Print port number for debugging purposes
                # Check if the port number starts with the correct prefix
                if port_number.startswith(port_prefix):
                    # Extract the third part of port number (1-52)
                    button_number = int(port_number.split('/')[-1])

                    # Check if port name contains "-lag1"
                    port_name = columns[1]
                    #print("Contents of port_name:", port_name)

                    # Check if the port_name contains "- lag1" with space
                    if "- lag1" in port_name:
                        #print("Found '- lag1' in port name:", port_name)
                        button_color = [0, 1, 0, 1]  # Green color for port containing "- lag1"
                    else:
                        # Find the button corresponding to the port number and update its color based on counters
                        button_color = [1, 1, 1, 1]  # Default color
                        try:
                            # Check if all values are numeric or '-'
                            if all(value.isdigit() or value == '-' for value in columns[2:]):
                                if any(int(value) != 0 for value in columns[2:]):
                                    button_color = [0, 1, 0, 1]  # Green color if any counter is not zero
                        except ValueError:
                            # Handle non-numeric values or dashes gracefully
                            print("Invalid counter value encountered, skipping...")

                        
                        
                        # Find the button corresponding to the port number and update its color

                        for button in self.children:
                            if isinstance(button, SwitchButton) and button.port_number == button_number:
                                # Check if any counter value is not zero
                                if any(value != '0' for value in columns[2:]):
                                    button_color = [0, 1, 0, 1]  # Set button color to green
                                else:
                                    button_color = [1, 1, 1, 1]  # Set button color to default

                               # print(f"Button color for port {port_number}: {button_color}")  # Print button color for debugging
                                button.background_color = button_color
                                #print(f"Port {port_number} mapped to button {button_number}")
                                break  # Exit the loop once the button is found and colored





    def show_counters(self, instance):
        selected_switch = self.manager.get_screen('menu').switch_menu.text
        selected_info = self.manager.get_screen('menu').switch_info.get(selected_switch)

        if selected_info is None:
            print(f"Error: No information found for selected switch '{selected_switch}'")
            return

        # Check if 'IPAddress' key is present
        if 'IPAddress' not in selected_info:
            print(f"Error: 'IPAddress' key not found in selected_info for switch '{selected_switch}'")
            return

        # Retrieve the IP address from selected_info
        ip_address = selected_info['IPAddress']

        # SSH into the switch and get counter output
        output = ssh_into_switch(ip_address, 'SWITCH USERNAME', 'SWITCH PASSWORD', 'sh interface statistics')

        if output:
            # Map port numbers to buttons based on the switch output
            self.map_ports_to_buttons(output)
            
            # Continue with other operations if needed
            # print("Output from the switch:")
            # print(output)
        else:
            # Display an error popup if SSH fails
            print("Failed to retrieve counters from the switch.")
            popup_content = Label(text="Failed to retrieve counters.")
            popup = Popup(title="Error", content=popup_content, size_hint=(None, None), size=(300, 200))
            popup.open()





    def update_button_colors(self, output):
        # Split the output into lines
        lines = output.strip().split('\n')

        # Remove header lines and separator lines
        lines = lines[4:]

        # Initialize a set to store interfaces with 0 counters
        zero_counter_interfaces = set()

        # Iterate over each line
        for line in lines:
            # Split the line into columns
            columns = line.split()
            # Check if all counter values are 0
            if all(value == '0' for value in columns[1:]):
                # If all counters are 0, add the interface to the set
                zero_counter_interfaces.add(columns[0])

        # Update buttons colors based on zero_counter_interfaces
        for button in self.children:
            if isinstance(button, SwitchButton) and str(button.port_number) in zero_counter_interfaces:
                button.background_color = [1, 1, 0, 1]  # Yellow color for buttons with zero counters
            else:
                button.background_color = [1, 1, 1, 1]  # Default color for other buttons


    def update_info(self, info):
        # Define coordinates for each button with spacing
        button_coordinates = {
            1: (40, 374),  2: (40, 338),  3: (82, 374),  4: (82, 338), 5: (125, 374),  6: (125, 338), 
            7: (168, 374),  8: (168, 338),  9: (210, 374),  10: (210, 338),
            11: (252, 374),  12: (252, 338),  13: (303, 374),  14: (303, 338),
            15: (346, 374),  16: (346, 338),  17: (388, 374),  18: (388, 338),
            19: (430, 374),  20: (430, 338),  21: (473, 374),  22: (473, 338),
            23: (516, 374),  24: (516, 338),
            # Additional rows of regular buttons
            25: (566, 374),  26: (566, 338),  27: (608, 374),  28: (608, 338),  29: (651, 374),  30: (651, 338),
            31: (693, 374),  32: (693, 338),  33: (736, 374),  34: (736, 338),
            35: (778, 374),  36: (778, 338),  37: (829, 374),  38: (829, 338),
            39: (871, 374),  40: (871, 338),  41: (913, 374),  42: (913, 338),
            43: (955, 374),  44: (955, 338),  45: (999, 374),  46: (999, 338),
            47: (1041, 374),  48: (1041, 338),
            #SFP+ buttons
            49: (1111, 382),   50: (1111, 335),   51: (1170, 382),  52: (1170, 335)
        }

        # Update switch information labels
        def update_info(self, info):
            # Update switch information labels
            if info:
                self.switch_info_label.text = f"Name: {info.get('SwitchName', '')}\nIP: {info.get('IPAddress', '')}\nVendor: {info.get('VendorType', '')}\nCurrent Switch in Stack: {self.active_switch}"


        # Add buttons to the layout
        for button_number, (x, y) in button_coordinates.items():
            button_width, button_height = (38, 20) if button_number <= 48 else (59, 24)

            # Determine the button color based on zero counters
            button_color = [1, 1, 0, 1] if str(button_number) in self.interfaces_with_zero_counters else [1, 1, 1, 1]

            button = SwitchButton(port_number=button_number, text=str(button_number),
                                size_hint=(None, None), size=(button_width, button_height),
                                pos=(x - button_width / 2, y - button_height / 2), background_color=button_color)
            self.add_widget(button)

    def increment_switch_number(self, instance):
        if self.current_switch_number + self.increment_value <= self.max_switch_number:
            self.current_switch_number += self.increment_value
            self.switch_number_label.text = f'Current Switch: {self.current_switch_number}'

    def decrement_switch_number(self, instance):
        if self.current_switch_number - self.increment_value >= 1:
            self.current_switch_number -= self.increment_value
            self.switch_number_label.text = f'Current Switch: {self.current_switch_number}'

    def go_to_home(self, instance):
        # Reset the active_switch variable to 1
        self.active_switch = 1

        # Close SSH connection if it's open
        if self.ssh_client:
            self.ssh_client.close()

        # Switch to the home screen
        self.manager.current = 'menu'


        # Switch to the home screen
        self.manager.current = 'menu'



class SwitchSelectApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(SwitchGUI(name='switch_gui'))  # Add switch GUI screen
        Window.size = (1280, 720)
        return sm

if __name__ == '__main__':
    SwitchSelectApp().run()
