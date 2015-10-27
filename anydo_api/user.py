#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json

from . import errors
from .constants import CONSTANTS

from .task import Task
from .category import Category

class User(object):
    """
    `User` is the class representing User object.
    It wraps user-related JSON into class instances and
    responsible for user management.
    """

    _endpoint = CONSTANTS.get('ME_URL')
    __reserved_attrs = ('data_dict', 'session', 'is_dirty')

    def __init__(self, session, data_dict):
        self.data_dict = data_dict
        self.session = session
        self.is_dirty = False

    def save(self):
        """
        Pushes updated attributes to the server.
        If nothing was changed we dont hit the API.
        """

        if self.is_dirty:
            headers = {
                'Content-Type' : 'application/json',
            }

            response_obj = self.session.put(
                CONSTANTS.get('ME_URL'),
                json=self.data_dict,
                headers=headers
            )

            try:
                response_obj.raise_for_status()
            except requests.exceptions.HTTPError as error:
                if response_obj.status_code == 400:
                    client_error = errors.BadRequestError(response_obj.content)
                elif response_obj.status_code == 409:
                    client_error = errors.ConflictError(response_obj.content)
                else:
                    client_error = errors.InternalServerError(error)

                client_error.__cause__ = None
                raise client_error

        self.is_dirty = False
        return self

    def destroy(self):
        """
        Hits the API to destroy the user.
        """

        headers = {
            'Content-Type': 'application/json',
            'AnyDO-Puid': str(self.data_dict['id'])
        }

        response_obj = self.session.delete(
            CONSTANTS.get('USER_URL'),
            json={ 'email': self.email, 'password': self.password },
            headers=headers
        )

        try:
            response_obj.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if response_obj.status_code == 400:
                client_error = errors.BadRequestError(response_obj.content)
            elif response_obj.status_code == 409:
                client_error = errors.ConflictError(response_obj.content)
            else:
                client_error = errors.InternalServerError(error)

            client_error.__cause__ = None
            raise client_error

        return self

    def tasks(self, refresh=False,
        include_deleted=False,
        include_done=False,
        include_checked=True,
        include_unchecked=True
    ):
        if not 'tasks_list' in self.__dict__ or refresh:
            params = {
                'includeDeleted': str(include_deleted).lower(),
                'includeDone': str(include_done).lower(),
            }

            tasks_data = self.session.get(
                CONSTANTS.get('TASKS_URL'),
                headers={
                    'Content-Type': 'application/json',
                    'Accept-Encoding': 'deflate'
                },
                params=params
            ).json()
            self.session.close()

            self.tasks_list = [ Task(data_dict=task, user=self) for task in tasks_data ]

        self.tasks_list

        return Task.filter_tasks(self.tasks_list,
                include_deleted=include_deleted,
                include_done=include_done,
                include_checked=include_checked,
                include_unchecked=include_unchecked
        )

    def categories(self, refresh=False, include_deleted=False):
        if not 'categories_list' in self.__dict__ or refresh:
            params = {
                'includeDeleted': str(include_deleted).lower(),
            }

            categories_data = self.session.get(
                CONSTANTS.get('CATEGORIES_URL'),
                headers={
                    'Content-Type': 'application/json',
                    'Accept-Encoding': 'deflate'
                },
                params=params
            ).json()
            self.session.close()

            self.categories_list = [ Category(data_dict=category, user=self) for category in categories_data ]

        result = self.categories_list
        if not include_deleted:
            result = list(filter(lambda cat: not cat['isDeleted'], result))

        return result

    def add_task(self, task):
        """
        Adds new task into internal storage.
        """

        if 'tasks_list' in self.__dict__:
            self.tasks_list.append(task)
        else:
            self.tasks_list = [task]

    def add_category(self, category):
        """
        Adds new category into internal storage.
        """

        if 'categories_list' in self.__dict__:
            self.categories_list.append(category)
        else:
            self.categories_list = [category]

    def default_category(self):
        """
        Returns defaul category for user if exist
        """
        return next((cat for cat in self.categories() if cat.isDefault), None)

    def pending_tasks(self, refresh=False):
        """
        Returns a list of dicts representing a pending task that was shared with current user.
        Empty list otherwise.
        """
        if not '_pending_tasks' in self.__dict__ or refresh:
            headers = {
                'Content-Type'   : 'application/json',
                'Accept'         : 'application/json',
                'Accept-Encoding': 'deflate',
            }

            response_obj = self.session.get(
                self.__class__._endpoint + '/pending',
                headers=headers
            )

            try:
                response_obj.raise_for_status()
            except requests.exceptions.HTTPError as error:
                if response_obj.status_code == 400:
                    client_error = errors.BadRequestError(response_obj.content)
                elif response_obj.status_code == 409:
                    client_error = errors.ConflictError(response_obj.content)
                else:
                    client_error = errors.InternalServerError(error)

                client_error.__cause__ = None
                raise client_error
            finally: self.session.close()

            self._pending_tasks = response_obj.json()['pendingTasks']

        return self._pending_tasks or []

    def pending_tasks_ids(self, refresh=False):
        """
        Returns a list of pending tasks ids shared with user.
        Empty list otherwise.
        """
        return [task['id'] for task in self.pending_tasks(refresh=refresh)]

    def approve_pending_task(self, pending_task_id=None, pending_task=None):
        """
        Approves pending task via API call.
        Accept pending_task_id or pending_task dict (in format of pending_tasks.
        """
        task_id = pending_task_id or pending_task['id']
        if not task_id:
            raise errors.AttributeError('Eather :pending_task_id or :pending_task argument is required.')

        headers = {
            'Content-Type'   : 'application/json',
            'Accept'         : 'application/json',
            'Accept-Encoding': 'deflate',
        }

        response_obj = self.session.post(
            self.__class__._endpoint + '/pending/' + task_id + '/accept',
            headers=headers
        )

        try:
            response_obj.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if response_obj.status_code == 400:
                client_error = errors.BadRequestError(response_obj.content)
            elif response_obj.status_code == 409:
                client_error = errors.ConflictError(response_obj.content)
            else:
                client_error = errors.InternalServerError(error)

            client_error.__cause__ = None
            raise client_error
        finally: self.session.close()

        return response_obj.json()

    def __getitem__(self, key):
        return self.data_dict[key]

    def __getattr__(self, attr):
        try:
            result = self.data_dict[attr]
        except KeyError:
            raise errors.AttributeError(attr + ' is not exist')

        return result

    def __setitem__(self, attr, new_value):
        if attr in self.data_dict:
            old_value = self.data_dict[attr]

            if old_value != new_value:
                self.data_dict[attr] = new_value
                self.is_dirty = True
        else:
            raise errors.AttributeError(attr + ' is not exist')

    def __setattr__(self, attr, new_value):
        if attr not in self.__class__.__reserved_attrs and attr in self.data_dict:
            old_value = self.data_dict[attr]

            if old_value != new_value:
                self.data_dict[attr] = new_value
                self.__dict__['is_dirty'] = True
        else:
            super(User, self).__setattr__(attr, new_value)

    @classmethod
    def create(klass, name, email, password, emails=None, phone_numbers=[]):
        """
        Creates new user by required parameters
        """
        headers = {
            'Content-Type' : 'application/json',
        }

        json_data = {
            'name': name,
            'username': email,
            'password': password,
            'emails': emails or email,
            'phoneNumbers': phone_numbers
        }

        session = requests.Session()
        response_obj = session.post(
            CONSTANTS.get('USER_URL'),
            json=json_data,
            headers=headers
        )

        try:
            response_obj.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if response_obj.status_code == 400:
                client_error = errors.BadRequestError(response_obj.content)
            elif response_obj.status_code == 409:
                client_error = errors.ConflictError(response_obj.content)
            else:
                client_error = errors.InternalServerError(error)

            client_error.__cause__ = None
            raise client_error
        finally: session.close()

        from .client import Client
        user = Client(email=email, password=password).me()
        return user

