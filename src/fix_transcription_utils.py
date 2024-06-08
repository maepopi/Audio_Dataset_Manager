import json
import os
import gradio as gr
import shutil

class AudioJsonHandler():
    """
        A handler for managing audio files and their corresponding JSON data.
    """
    
    def __init__(self):
        self.json_data = None
        self.json_path = None
        self.audio_folder = None
        self.keep_start_audio = False
        self.keep_end_audio = False
    
    def get_json(self, path,):
        """
            Retrieve the first JSON file from the specified directory that doesn't contain
            'backup', 'discarded', or 'unsanitized' in its filename.

            Args:
                path (str): The directory to search for JSON files.

            Returns:
                str: The filename of the JSON file if found, else None.
        """
        return next(
        (file for file in os.listdir(path) if file.endswith('.json') 
                                            and 'backup' not in file 
                                            and 'discarded' not in file
                                            and 'unsanitized' not in file), None)

    def load_and_init(self, json_folder, *all_segment_boxes, total_segment_components):
        """
            Load the initial JSON file and create a backup.

            Args:
                json_folder (str): The folder containing the JSON file.
                all_segment_boxes (tuple): All segment boxes.
                total_segment_components (int): The total number of segment components.

            Returns:
                list: Updated UI components after initialization.
        """

        original_json_file = self.get_json(json_folder)
        original_json_path = os.path.join(json_folder, original_json_file)
        self.audio_folder = os.path.join(json_folder, "audio")

        # Create a backup
        json_name = os.path.splitext(original_json_file)[0]
        backup_json_file = f'{json_name}_backup.json'
        backup_json_path = os.path.join(json_folder, backup_json_file)

        shutil.copy(original_json_path, backup_json_path)

   
        self.json_path = os.path.join(json_folder, original_json_file)

        # We load the json data into the class parameter
        with open(self.json_path, 'r') as file:
            self.json_data = json.load(file)

        return self.update_UI(0, json_folder, *all_segment_boxes, total_segment_components=total_segment_components)

    def delete_multiple(self, json_folder, index, start_audio, end_audio, index_format, total_segment_components):
        """
            Delete multiple entries from the JSON file and update the UI accordingly.

            Args:
                json_folder (str): The folder containing the JSON file.
                index (int): The current index in the UI.
                start_audio (str): The start audio index.
                end_audio (str): The end audio index.
                index_format (str): The format of the index.
                total_segment_components (int): The total number of segment components.

            Returns:
                list: Updated UI components after deletion.
        """

        # In this particular case, the delete start and end boxes are not empty but we WANT them to be cleared after clicking the button.
        # That is why we needed to add these two boolean as class variables, to be able to manage the clearing depending on the process
        self.keep_start_audio = False
        self.keep_end_audio = False

        index_format = '06d' if index_format is None else f'0{str(index_format)}d'
        
        try:
            start_audio_int = int(start_audio)
            end_audio_int = int(end_audio)

        except ValueError:
            # If values are not ints, stay on same page and raise an error. Index-1 ensure the page doesn't change
            return self.update_UI(index-1, json_folder, total_segment_components=total_segment_components, info_message="Start and End values must be integers.")

        if start_audio_int > 999999 or end_audio_int > 999999:
            return self.update_UI(index-1, json_folder, total_segment_components=total_segment_components, info_message="Start and End values must be within 6 digits.")

        if start_audio_int >= end_audio_int:
            return self.update_UI(index-1, json_folder, total_segment_components=total_segment_components, info_message="Start value must be smaller than End value.")

        # Formatting the keys
        formatted_start_index= f"{start_audio_int:{index_format}}"
        formatted_end_index = f"{end_audio_int:{index_format}}"
        start_key, end_key = None, None


        # Iterate through all keys to find exact matches for the start and end indices
        for key in self.json_data.keys():
            if formatted_start_index in key:
                start_key = key
            if formatted_end_index in key:
                end_key = key
            # Break out of the loop if both start and end keys are found
            if start_key and end_key:
                break

        # Collect the keys to delete
        keys_to_delete = []

        for key in self.json_data.keys():
            if start_key is None:
                return self.update_UI(index-1, json_folder, total_segment_components=total_segment_components, info_message="Start key couldn't be found.")

            if end_key is None:
                return self.update_UI(index-1, json_folder, total_segment_components=total_segment_components, info_message="End key couldn't be found.")

            if start_key <= key <= end_key:
                keys_to_delete.append(key)




        return self.delete_entries(json_folder, index, keys_to_delete, total_segment_components, audios_to_delete=len(keys_to_delete))

        


    def delete_entries(self, json_folder, index, audio_names, total_segment_components, audios_to_delete=1):
        """
            Delete entries from the JSON and audio folders and update the UI accordingly.

            Args:
                json_folder (str): The folder containing the JSON file.
                index (int): The current index in the UI.
                audio_names (list): The names of audio entries to delete.
                total_segment_components (int): The total number of segment components.
                audios_to_delete (int): The number of audios to delete.

            Returns:
                list: Updated UI components after deletion.
        """
         
        # Part of this function gets repeated with save json, needs refactor
        def delete_from_JSON(discard_folder):
            """
                Deletes specified entries from the JSON data, moves them to a discard folder, and updates related files.

                Args:
                    discard_folder (str): The folder path where the discarded entries will be moved.
            """
                
            discarded_entries_path = os.path.join(discard_folder, 'discarded_entries.json')
            discarded_entries = {}

            # Opening the JSON and loading its contents
            with open(self.json_path, 'r+') as file:
                self.json_data = json.load(file)

                # If there is only one entry in the JSON, return an error
                if len(self.json_data) <= 1:
                    log_message = 'Cannot delete the last audio of the dataset'
                    return self.update_UI(index, json_folder, total_segment_components=total_segment_components, info_message=log_message)

                # Remove the specified entries and store them for later
                for audio_name in audio_names:

                    if audio_name in self.json_data:
                        discarded_entries[audio_name] = self.json_data.pop(audio_name)

                    else:
                        print(f'Audio name {audio_name} not found in JSON data')

                # Going back to the start of the file so that we can replace everything with the updated data
                file.seek(0)
                json.dump(self.json_data, file, indent=4)

                # Truncating at the current position of the cursor so that no extra information is added by accident
                file.truncate()

            # If the discarded JSON entry file doesn't exist, create it and add the deleted entries if there are any
            if discarded_entries:
                if not os.path.exists(discarded_entries_path):
                    with open(discarded_entries_path, 'w') as discarded_json_file:
                        json.dump(discarded_entries, discarded_json_file, indent=4)

                # If the discarded JSON entry file exists, oppen it and append the deleted entry
                else:
                    with open(discarded_entries_path, 'r+') as discarded_json_file:
                        discarded_json_data = json.load(discarded_json_file)
                        discarded_json_data.update(discarded_entries)    
                        discarded_json_file.seek(0)
                        json.dump(discarded_json_data, discarded_json_file, indent=4)
                        discarded_json_file.truncate()


        def delete_from_audios(discard_folder):
            """
                Moves specified audio files from the main audio folder to a designated discard folder.

                Args:
                    discard_folder (str): The folder path where the discarded audio files will be moved.
            """

            deleted_audio_folder = os.path.join(discard_folder, "Discarded_Audios")
            os.makedirs(deleted_audio_folder, exist_ok=True)

            for audio in os.listdir(self.audio_folder):
                if audio in audio_names:
                    src = os.path.join(self.audio_folder, audio)
                    dst = os.path.join(deleted_audio_folder, audio)

                    try:
                        shutil.move(src, dst)

                    except Exception as e:
                        print(f"Error moving {src} to {dst}: {e}")


        # Ensure audio_names is a list so that we can treat both the cases where we delete a single or multiple entries
        if not isinstance(audio_names, list):
            audio_names = [audio_names]

        discard_folder = os.path.join(json_folder, "Discarded")
        os.makedirs(discard_folder, exist_ok=True)


        delete_from_JSON(discard_folder)
        delete_from_audios(discard_folder)


        if audios_to_delete:
            if audios_to_delete == 1:
                log_message = f'{audio_names} was successfully deleted from the dataset.'

            else:
                log_message = f'{audio_names} were successfully deleted from the dataset.'

        else:
            log_message = 'There are no audios to be deleted.'


        return self.update_UI(index - 1, json_folder, total_segment_components=total_segment_components, info_message=log_message)


    def save_json(self, json_folder, text, audio_name, *all_segment_boxes):
        """
            Save updates to the JSON file with new text and segment data.

            Args:
                json_folder (str): The folder containing the JSON file.
                text (str): The updated text for the audio.
                audio_name (str): The name of the audio entry to update.
                all_segment_boxes (tuple): The segment data to update.

            Returns:
                str: A confirmation message after saving the JSON.
        """
                
        def process_json(file, text, audio_name, cleaned_textboxes):
            """
                Processes the JSON file by updating the text and segment information for a specific audio file.

                Args:
                    file (file): The JSON file to be processed.
                    text (str): The new text to be assigned to the audio file.
                    audio_name (str): The name of the audio file to be updated.
                    cleaned_textboxes (list): A list of cleaned text and time values for segments.

                Raises:
                    ValueError: If there is an error converting time values to float.
            """
            

            self.json_data = json.load(file)
            self.json_data[audio_name]['text'] = text
            segments = self.json_data[audio_name]['segments']

            for i, segment in enumerate(segments):
                # The list makes the texts, starts and ends follow by groups of three. We need to parse with a delta.
                j = i*3

                try:
                    # Ensure start and end times are floats so they are written as floats in the JSON
                    start_time = float(cleaned_textboxes[j+1])
                    end_time = float(cleaned_textboxes[j+2])

                except ValueError as e:
                    print(f"Error converting time values to float: {e}")
                    continue  # Skip this iteration if error, and continue with the next
        

                # Assigning the cleaned and converted values to the segments
                segment['text'] = cleaned_textboxes[j]
                segment['start'] = start_time
                segment['end'] = end_time

            file.seek(0)
            json.dump(self.json_data, file, indent=4)
            file.truncate()
    
        json_file = self.get_json(json_folder)
        json_file_path = os.path.join(json_folder, json_file)

        # Avoids returning empty strings
        cleaned_textboxes= [i for i in all_segment_boxes if i]
        

        with open(json_file_path, 'r+') as file:
            process_json(file, text, audio_name, cleaned_textboxes)
        return 'The JSON was saved.'


    def handle_pagination(self, page, json_folder, delete_start_audio, delete_end_audio, delta=None, go_to=None, total_segment_components=None):
        """
            Handle pagination of audio entries, adjusting the current index based on user interaction.

            Args:
                page (int): The current page number.
                json_folder (str): The folder containing the JSON file.
                delete_start_audio (str): The start audio deletion index.
                delete_end_audio (str): The end audio deletion index.
                delta (int, optional): The change in page number to apply. Defaults to None.
                go_to (int, optional): The specific page number to go to. Defaults to None.
                total_segment_components (int, optional): The total number of segment components. Defaults to None.

            Returns:
                list: Updated UI components based on the new page index.
        """


        new_index = page - 1

        if delta:
            new_index = new_index + delta # We adjust for zero-based indexing, and the delta determines which way we move
        
        elif go_to:
            new_index = go_to

        # Checking whether there's something written in the delete start and end audio textboxes. If they are not empty, we need to keep them 
        self.keep_start_audio = delete_start_audio != ""
        self.keep_end_audio = delete_end_audio != ""

        # Check if the new_index is within the valid range
        if 0 <= new_index < len(self.json_data):
            return self.update_UI(new_index, json_folder, total_segment_components=total_segment_components, delete_start_audio=delete_start_audio, delete_end_audio=delete_end_audio)
        else:
            # If the new_index is out of bounds, return current state without change
            # To achieve this, subtract delta to revert to original page index
            return self.update_UI(page - 1, json_folder, delete_start_audio, delete_end_audio, total_segment_components=total_segment_components)  # page - 1 adjusts back to zero-based index

            
    def update_UI(self, index, json_folder, *all_segment_boxes, total_segment_components=None, info_message="", delete_start_audio=None, delete_end_audio=None):
        """
            Update the UI based on the current audio index.

            Args:
                index (int): The current index of the audio entry.
                json_folder (str): The folder containing the JSON file.
                all_segment_boxes (tuple): All segment boxes.
                total_segment_components (int, optional): The total number of segment components. Defaults to None.
                info_message (str, optional): Additional information message to display. Defaults to "".
                delete_start_audio (str, optional): The start audio deletion index. Defaults to None.
                delete_end_audio (str, optional): The end audio deletion index. Defaults to None.

            Returns:
                list: Updated UI components based on the current audio index.
        """
        def get_audio_file():
            """
                Returns the key at the specified index from the JSON data.

                Returns:
                    str: The key at the specified index from the JSON data.
            """
            keys_list = list(self.json_data.keys())
            return keys_list[index]

        def get_JSON_reference(audio_name):
            """
                Returns the text associated with the provided audio name from the JSON data.

                Args:
                    audio_name (str): The name of the audio file.

                Returns:
                    str: The text associated with the provided audio name from the JSON data.
            """
            return self.json_data[audio_name]['text']

        def create_segment_group(segments):
            """
                Creates a group of UI components for each segment with text, start, and end values.

                Args:
                    segments (list): A list of segment dictionaries containing text, start, and end values.

                Returns:
                    list: A list of UI components for each segment with corresponding text, start, and end values.
            """
            new_segment_group = []

            visible_segments = len(segments) if segments else 0  

            for i in range(total_segment_components):
                # If there are no segments at all, then all boxes should be invisible. Otherwise, only the right amount of boxes should be visible.
                visible = False if visible_segments == 0 else i < visible_segments

                # Get the right keys for the text, start and end
                text = segments[i].get('text', '') if visible and segments else ''
                start = segments[i].get('start', '') if visible and segments else ''
                end = segments[i].get('end', '') if visible and segments else ''

                # Create UI components
                # Components should be visible only if they correspond to an actual segment
                seg_textbox = gr.Textbox(visible=visible, value=text, label=f'Segment {i+1} Text', interactive=True, scale=50)
                start_number = gr.Textbox(visible=visible, value=str(start), label=f'Segment {i+1} Start', interactive=True)
                end_number = gr.Textbox(visible=visible, value=str(end), label=f'Segment {i+1} End', interactive=True)

                # Extend the group with the new components
                new_segment_group.extend([seg_textbox, start_number, end_number])

            return new_segment_group


        # Initializing segment creation
        new_segment_group = create_segment_group(None) # Initialize with default empty segments

        # Retrieving the current amount of entries in the JSON
        audio_amount = len(self.json_data)

        # Clearing the "delete multiple" start and end textboxes according to the right situation
        if self.keep_start_audio == False:
            delete_start_audio = gr.update(value="")

        if self.keep_end_audio == False:
            delete_end_audio = gr.update(value="")

        if index < 0:
            index = 0  
        elif index >= audio_amount:
            index = audio_amount - 1  # If the user tries to go to a page out of range, he's drawn back to the last audio

        # Updating the UI with the correct audio information
        if 0 <= index < audio_amount:
            audio_file = get_audio_file()
            audio_name = os.path.basename(audio_file)
            audio_path = os.path.join(json_folder, self.audio_folder, audio_file) #the name of the audio folder should NOT be hard coded
            JSON_reference = get_JSON_reference(audio_name)
            current_page_label = f"Current Audio: {index + 1}/{audio_amount}"

            if not JSON_reference:  # If 'text' key is empty
                info_message = "There are no segments or text available for this audio."
                return [audio_path, audio_name, index + 1, current_page_label, JSON_reference, info_message, delete_start_audio, delete_end_audio] + new_segment_group

            # Loading the segments related to the audio
            segments = self.json_data[audio_name].get('segments', [])
            new_segment_group = create_segment_group(segments)



            return [audio_path, audio_name, index + 1, current_page_label, JSON_reference, info_message, delete_start_audio, delete_end_audio] + new_segment_group


        # If there was a problem in loading the audio
        new_segment_group = all_segment_boxes
        audio_path = None
        audio_name = ""
        current_page_label = "Audio not available"
        JSON_reference = ""
        info_message = "Something went wrong. Check whether your JSON file is empty."

        return [audio_path, audio_name, 1, current_page_label, JSON_reference, info_message, delete_start_audio, delete_end_audio] + new_segment_group
            
            


