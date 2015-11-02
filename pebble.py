#!/usr/bin/env python
import uuid
import sys
import shelve
import json
import time
import pika
import getopt

class PebbleRpcClient(object):
    def __init__(self):

	self.credentials = pika.PlainCredentials('pi','raspberry')

	self.connection = pika.BlockingConnection(pika.ConnectionParameters(
        	'10.0.0.134', 5672, '/', self.credentials))


        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)
	
	self.dataStore = shelve.open("shelf.db")

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def send(self, n, action):
	print("action", action)
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='rpc_queue',
                                   properties=pika.BasicProperties(
                                         reply_to = self.callback_queue,
                                         correlation_id = self.corr_id,
                                         ),
                                   body=str(n))
        while self.response is None:
            self.connection.process_data_events()
	if action == 'pull':
		json_resp = json.loads(self.response)
		if json_resp ==  None:
			print("Pull request could not be fulfilled.")
			return self.response
		msgID = json_resp['msgID']
		msgID = str(msgID)	
        	print("pulled message id", msgID)
        	self.dataStore[msgID] = self.response
        	print("Put in the data store", self.dataStore[msgID])
		print("Contents of dataStore", self.dataStore)
        
	return self.response

    def pull(self, n):
	print("action", "pull")
	self.response = None
        self.corr_id = str(uuid.uuid4())
        print self.channel.basic_get(self.callback_queue)
	while self.response is None:
            self.connection.process_data_events()
	msgID = self.response['msgID']
	print("pulled message id", msgID)
	self.dataStore[msgID] = self.response
	print("Put in the data store", self.dataStore[msgID])
        return self.response


def main(argv):

        pebble_rpc = PebbleRpcClient()

	try:
        	opts, args = getopt.getopt(sys.argv[1:], "hoa:m:s:v", ["help", "output=", "Qs=", "Qm=", "Qa=", "QA="])
    	except getopt.GetoptError as err:
        	# print help information and exit:
        	print str(err) # will print something like "option -a not recognized"
        	#usage()
       		sys.exit(2)
    	output = None
    	verbose = False

	message = None
	subject = None
	action = None
	queryMessage = None
	querySubject = None
	queryAge = 73
	queryAuthor = 'Freddy Kreuger'

    	for o, a in opts:
        	if o == "-v":
           		verbose = True
        	elif o in ("-h", "--help"):
            		usage()
            		sys.exit()
        	elif o in ("-o", "--output"):
            		output = a
		elif o == "-m":
			message = a
		elif o == "-s":
			subject = a
		elif o == "-a":
			action = a
		elif o == "--Qm":
			queryMessage = a
		elif o == "--QA":
			queryAuthor = a
		elif o == "--Qa":
			queryAge = int(a)
		elif o == '--Qs':
			querySubject = a
        	else:	
            		assert False, "unhandled option"

	data = {}
	epoch_seconds = time.mktime(time.localtime())
	data['msgID'] = 'Team21_' + str(epoch_seconds)
	data['author'] = 'Freddy Kreuger'
        data['age'] = 73
	data['action'] = action

        if action == "pull" or action == "pullr":
		data['message'] = queryMessage
		data["subject"] = querySubject
		data["age"] = queryAge
		data["author"] = queryAuthor
        elif action == "push":
                data['subject'] = subject
                data['message'] = message
        else: 
		pass  
	json_data = json.dumps(data)
	print ("Message", json_data)
	
	response = pebble_rpc.send(json_data, action)
	print ("Response", response)
	
	pebble_rpc.dataStore.close()

if __name__ == "__main__":
    main(sys.argv)
