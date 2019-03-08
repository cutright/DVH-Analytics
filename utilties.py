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
    is_uid_in_table = {table: uid in table_uids for table, table_uids in uids.items()}
    return all([list(is_uid_in_table.values())])


def flatten_list_of_lists(some_list, remove_duplicates=False, sort=False):
    data = [item for sublist in some_list for item in sublist]
    if sort:
        data.sort()
    if remove_duplicates:
        return list(set(data))
    return data
