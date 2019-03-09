from db.sql_connector import DVH_SQL


def get_study_instance_uids(**kwargs):
    cnx = DVH_SQL()
    uids = {table: cnx.get_unique_values(table, 'study_instance_uid', condition) for table, condition in kwargs.items()}
    cnx.close()

    complete_list = flatten_list_of_lists(list(uids.values()), remove_duplicates=True)

    uids['common'] = [uid for uid in complete_list if is_uid_in_all_keys(uid, uids)]
    uids['unique'] = complete_list

    return uids


def is_uid_in_all_keys(uid, uids):
    key_answer = {}
    # Initialize a False value for each key
    for key in list(uids):
        key_answer[key] = False
    # search for uid in each keyword fof uid_kwlist
    for key, value in uids.items():
        if uid in value:
            key_answer[key] = True

    final_answer = True
    # Product of all answer[key] values (except 'unique')
    for key, value in key_answer.items():
        if key not in 'unique':
            final_answer *= value
    return final_answer


def flatten_list_of_lists(some_list, remove_duplicates=False, sort=False):
    data = [item for sublist in some_list for item in sublist]
    if sort:
        data.sort()
    if remove_duplicates:
        return list(set(data))
    return data


def collapse_into_single_dates(x, y):
    """
    :param x: a list of dates in ascending order
    :param y: a list of values as a function of date
    :return: a unique list of dates, sum of y for that date, and number of original points for that date
    :rtype: dict
    """

    # average daily data and keep track of points per day
    x_collapsed = [x[0]]
    y_collapsed = [y[0]]
    w_collapsed = [1]
    for n in range(1, len(x)):
        if x[n] == x_collapsed[-1]:
            y_collapsed[-1] = (y_collapsed[-1] + y[n])
            w_collapsed[-1] += 1
        else:
            x_collapsed.append(x[n])
            y_collapsed.append(y[n])
            w_collapsed.append(1)

    return {'x': x_collapsed, 'y': y_collapsed, 'w': w_collapsed}


def moving_avg(xyw, avg_len):
    """
    :param xyw: a dictionary of of lists x, y, w: x, y being coordinates and w being the weight
    :param avg_len: average of these number of points, i.e., look-back window
    :return: list of x values, list of y values
    """
    cumsum, moving_aves, x_final = [0], [], []

    for i, y in enumerate(xyw['y'], 1):
        cumsum.append(cumsum[i - 1] + y / xyw['w'][i - 1])
        if i >= avg_len:
            moving_ave = (cumsum[i] - cumsum[i - avg_len]) / avg_len
            moving_aves.append(moving_ave)
    x_final = [xyw['x'][i] for i in range(avg_len - 1, len(xyw['x']))]

    return x_final, moving_aves


def convert_value_to_str(value, round=2):
    try:
        formatter = "%%0.%df" % round
        return formatter % value
    except TypeError:
        return value
