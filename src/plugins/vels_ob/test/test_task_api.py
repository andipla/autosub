# coding: utf-8

"""
    HDL Testing Platform

    REST API for HDL TP  # noqa: E501

    OpenAPI spec version: 1.0
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""


from __future__ import absolute_import

import unittest

import swagger_client
from swagger_client.api.task_api import TaskApi  # noqa: E501
from swagger_client.rest import ApiException


class TestTaskApi(unittest.TestCase):
    """TaskApi unit test stubs"""

    def setUp(self):
        self.api = swagger_client.api.task_api.TaskApi()  # noqa: E501

    def tearDown(self):
        pass

    def test_create_a_new_task(self):
        """Test case for create_a_new_task

        Creates a new Task  # noqa: E501
        """
        pass

    def test_delete_a_task(self):
        """Test case for delete_a_task

        delete a task given its identifier  # noqa: E501
        """
        pass

    def test_get_a_bit(self):
        """Test case for get_a_bit

        get a tasks bit file given its identifier  # noqa: E501
        """
        pass

    def test_get_a_task(self):
        """Test case for get_a_task

        get a task given its identifier  # noqa: E501
        """
        pass

    def test_list_of_tasks(self):
        """Test case for list_of_tasks

        List all registered tasks  # noqa: E501
        """
        pass

    def test_set_a_task_inactive(self):
        """Test case for set_a_task_inactive

        set a task inactive given its identifier  # noqa: E501
        """
        pass


if __name__ == '__main__':
    unittest.main()
