########################################################################
# test_fetcher.py -- unittests for fetcher.py
#
# Copyright (C) 2015 Andreas Platschek <andi.platschek@gmail.com>
# License GPL V2 or later (see http://www.gnu.org/licenses/gpl2.txt)
########################################################################
import threading, queue
import unittest
import mock
import fetcher
from fetcher import mailFetcher
import sqlite3 as lite
import logger
import time
import configparser as CP
import imaplib
import common

class Test_mailFetcher(unittest.TestCase):
   def setUp(self):
      self.name = "testfecher"
      self.logger_queue = queue.Queue(10)
      mailFetcher.logger_queue = self.logger_queue
      #Before we do anything else: start the logger thread, so we can log whats going on
      threadID=1
      logger_t = logger.autosubLogger(threadID, "logger", mailFetcher.logger_queue)
      logger_t.daemon = True # make the logger thread a daemon, this way the main
                      # will clean it up before terminating!
      logger_t.start()

   # two cases: either the user is whitelisted, or not, so both are tested,
   # after that the testuser is removed from the table (for the next run)
   def test_check_if_whitelisted(self):
      con = lite.connect('semester.db')
      cur = con.cursor()
      result = mailFetcher.check_if_whitelisted(self, cur, con, "testuser@test.com")
      self.assertEqual(result, 0)
      # add the user, then check again!
      sqlcmd = "INSERT INTO WhiteList (Email) VALUES('testuser@test.com')"
      cur.execute(sqlcmd)
      result = mailFetcher.check_if_whitelisted(self , cur, con, "testuser@test.com")
      self.assertEqual(result, 1)

      sqlcmd = "DELETE from WhiteList WHERE Email=='testuser@test.com'"
      cur.execute(sqlcmd)

   def mock_connect_to_imapserver(self):
      # just use any arbitraray IMAP server -- we are not going to login
      # anyway!
      return imaplib.IMAP4_SSL('imap.gmail.com')

   def mock_fetch_new_emails(self, m):
      return self.testcases

   def mock_fetch(self, mailid, encoding):
      config = CP.ConfigParser()
      config.readfp(open('tests/fetcher_testcases.cfg'))
      resp = eval(str(config.get(str(mailid), 'resp')))
      data = eval(str(config.get(str(mailid), 'data')))
      return resp, data

   def get_userid_by_email(self, email):
      #connect to the semester database, and assure, that the e-mail(user) in the test
      #cases is not yet whitelisted (from some other test).
      con = lite.connect('semester.db')
      cur = con.cursor()
      sqlcmd = "SELECT UserId FROM Users WHERE Email=='" + email + "';"
      cur.execute(sqlcmd)
      res = cur.fetchone()
      if str(res) != 'None':
         userid = str(res[0])
      else:
         userid = "0"
      con.close()
      return userid

   def delete_user_by_email(self, email):
      con = lite.connect('semester.db')
      cur = con.cursor()
      sqlcmd = "DELETE FROM Users WHERE Email=='" + email + "';"
      cur.execute(sqlcmd)
      con.commit()
      con.close()

   def delete_email_from_whitelist(self, email):
      con = lite.connect('semester.db')
      cur = con.cursor()
      sqlcmd = "DELETE FROM WhiteList WHERE Email=='" + email + "';"
      cur.execute(sqlcmd)
      con.commit()
      con.close()

   def insert_email_to_whitelist(self, email):
      con = lite.connect('semester.db')
      cur = con.cursor()
      sqlcmd = "INSERT INTO WhiteList (Email) VALUES('" + email + "');"
      cur.execute(sqlcmd)
      con.commit()
      con.close()

   def set_adminmail_set(self, email):
      curc, conc = common.connect_to_db('course.db', self.logger_queue, "testfetcher")
      sqlcmd = "UPDATE GeneralConfig SET Content='" + str(email) + "' WHERE ConfigItem == 'admin_email'"
      curc.execute(sqlcmd)
      conc.commit()
      conc.close()

   def get_statcounter(self, countername):
      con = lite.connect('semester.db')
      cur = con.cursor()
      sqlcmd = "SELECT Value FROM StatCounters WHERE Name=='" + countername + "';"
      cur.execute(sqlcmd)
      res = cur.fetchone()
      value = str(res[0])
      return value

   def test_loop_code(self):
      job_queue = queue.Queue(10)
      sender_queue = queue.Queue(10)
      gen_queue = queue.Queue(10)
      mf = mailFetcher(3, "testfetcher", job_queue, sender_queue, gen_queue, "autosub_testuser", "autosub_test_passwd", "imap.testdomain.com", self.logger_queue, 1)
     
      self.delete_user_by_email("platschek@ict.tuwien.ac.at")
      old_nrfetched=self.get_statcounter('nr_mails_fetched')

      #TESTCASE1: try to register user not on the whitelist:
      self.delete_email_from_whitelist('platschek@ict.tuwien.ac.at')
      old_nonreg=self.get_statcounter('nr_non_registered')
      with mock.patch.multiple('fetcher.mailFetcher',
                               connect_to_imapserver=self.mock_connect_to_imapserver,
                               fetch_new_emails=self.mock_fetch_new_emails):
         with mock.patch("imaplib.IMAP4.fetch", self.mock_fetch):
            self.testcases = [b'10']
            mf.loop_code()

            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "platschek@ict.tuwien.ac.at")
            self.assertEqual(sendout.get('message_type'), "NotAllowed")
            self.assertEqual(sendout.get('Task'), "")
            self.assertEqual(str(int(old_nonreg)+1), self.get_statcounter('nr_non_registered'))

      #TESTCASE2: try to register user on the whitelist:
      self.insert_email_to_whitelist('platschek@ict.tuwien.ac.at')
      with mock.patch.multiple('fetcher.mailFetcher',
                               connect_to_imapserver=self.mock_connect_to_imapserver,
                               fetch_new_emails=self.mock_fetch_new_emails):
         with mock.patch("imaplib.IMAP4.fetch", self.mock_fetch):
            self.testcases = [b'10']  
            mf.loop_code()

            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "platschek@ict.tuwien.ac.at")
            self.assertEqual(sendout.get('message_type'), "Task")
            self.assertEqual(sendout.get('Task'), "1")

            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "platschek@ict.tuwien.ac.at")
            self.assertEqual(sendout.get('message_type'), "Welcome")
            self.assertEqual(sendout.get('Task'), "")

      #TESTCASE3: try to get a status report for a registered user:
      old_sreq = self.get_statcounter('nr_status_requests')
      with mock.patch.multiple('fetcher.mailFetcher',
                               connect_to_imapserver=self.mock_connect_to_imapserver,
                               fetch_new_emails=self.mock_fetch_new_emails):
         with mock.patch("imaplib.IMAP4.fetch", self.mock_fetch):
            self.testcases = [b'11']  
            mf.loop_code()

            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "platschek@ict.tuwien.ac.at")
            self.assertEqual(sendout.get('message_type'), "Status")
            self.assertEqual(sendout.get('Task'), "1")
            self.assertEqual(str(int(old_sreq)+1), self.get_statcounter('nr_status_requests'))

      #TESTCASE4: task submission for Invalid task:
      with mock.patch.multiple('fetcher.mailFetcher',
                               connect_to_imapserver=self.mock_connect_to_imapserver,
                               fetch_new_emails=self.mock_fetch_new_emails):
         with mock.patch("imaplib.IMAP4.fetch", self.mock_fetch):
            self.testcases = [b'13']  
            mf.loop_code()

            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "platschek@ict.tuwien.ac.at")
            self.assertEqual(sendout.get('message_type'), "InvalidTask")
            self.assertEqual(sendout.get('Task'), "")

      #TESTCASE5: A user sends a question:
      self.set_adminmail_set('administrator@testdomain.com')
      old_nrq = self.get_statcounter('nr_questions_received')
      with mock.patch.multiple('fetcher.mailFetcher',
                               connect_to_imapserver=self.mock_connect_to_imapserver,
                               fetch_new_emails=self.mock_fetch_new_emails):
         with mock.patch("imaplib.IMAP4.fetch", self.mock_fetch):
            self.testcases = [b'12']  
            mf.loop_code()

            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "platschek@ict.tuwien.ac.at")
            self.assertEqual(sendout.get('message_type'), "Question")
            self.assertEqual(sendout.get('Task'), "")
            
            self.assertEqual(str(int(old_nrq)+1), self.get_statcounter('nr_questions_received'))
          
            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "administrator@testdomain.com")
            self.assertEqual(sendout.get('message_type'), "QFwd")
            self.assertEqual(sendout.get('Task'), "")

      # the nr. of fetched e-mails should have gone up by 5 now.
      self.assertEqual(str(int(old_nrfetched)+5), self.get_statcounter('nr_mails_fetched'))

      #TESTCASE6: Trigger a Usage message:
      with mock.patch.multiple('fetcher.mailFetcher',
                               connect_to_imapserver=self.mock_connect_to_imapserver,
                               fetch_new_emails=self.mock_fetch_new_emails):
         with mock.patch("imaplib.IMAP4.fetch", self.mock_fetch):
            self.testcases = [b'10']  
            mf.loop_code()

            sendout = sender_queue.get()
            self.assertEqual(sendout.get('recipient'), "platschek@ict.tuwien.ac.at")
            self.assertEqual(sendout.get('message_type'), "Usage")
            self.assertEqual(sendout.get('Task'), "")
            
      # the nr. of fetched e-mails should have gone up by 6 now.
      self.assertEqual(str(int(old_nrfetched)+6), self.get_statcounter('nr_mails_fetched'))

if __name__ == '__main__':
   unittest.main()
