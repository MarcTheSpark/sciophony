""" This function takes in an array as an argument and returns a new array
that contains all the items of the input array, sorted by their frequency.
The function uses a dictionary to keep track of the frequency of each item in the array. T
hen the function sorts the dictionary by the values (frequencies) in descending order. Finally, it extracts
the items from the sorted list of tuples and return them as an array.
For example, if you call sort_by_frequency([1, 2, 3, 2, 1, 3, 1]), the function will return [1, 2, 3].
Note that the order of the items with the same frequency is not defined. """


def sort_by_frequency(arr):
    # Create an empty dictionary
    freq_dict = {}
    # Iterate over the array
    for item in arr:
        # If the item is already in the dictionary, increment its count
        if item in freq_dict:
            freq_dict[item] += 1
        # If the item is not in the dictionary, add it with a count of 1
        else:
            freq_dict[item] = 1
    # Sort the dictionary by the values (frequencies)
    sorted_items = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)
    # Extract the items from the sorted list of tuples
    sorted_arr = [item[0] for item in sorted_items]
    return sorted_arr
