from flask import Flask
from flask_restful import Api
from flask_restful import Resource, abort, reqparse
from datetime import datetime
import uuid
import json

USERS = {}

class User:
    
    def __init__(self, user_id = uuid.uuid4().hex, surname = "muster", firstname = "max", street = "fhnwstreet", postcode = 0, city = "New York" ):
        self._user_id = user_id
        self._surname = surname
        self._firstname = firstname
       
        self._create_time = str(datetime.now(tz=None))

        self._street = street
        self._postcode = postcode
        self._city = city

        self._access_permitted = "no"
        self._state = "out"

        self._connection_id = ""
        
    @property
    def surname(self):
        return self._surname
    
    @surname.setter
    def surname(self, value):
        self._surname = value

    @property
    def connection_id(self):
        return self._connection_id
    
    @connection_id.setter
    def connection_id(self, value):
        self._connection_id = value

    @property
    def firstname(self):
        return self._firstname
    
    @firstname.setter
    def firstname(self, value):
        self._firstname = value
    
    @property
    def postcode(self):
        return self._postcode
    
    @postcode.setter
    def postcode(self, value):
        self._postcode = value

    @property
    def street(self):
        return self._street
    
    @street.setter
    def street(self, value):
        self._street = value

    @property
    def city(self):
        return self._city
    
    @city.setter
    def city(self, value):
        self._city = value
    
    @property
    def access_permitted(self):
        return self._access_permitted
    
    @access_permitted.setter
    def access_permitted(self, value):
        self._access_permitted = value
    
    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, value):
        self._state = value
    
    @property
    def user_id(self):
        return self._user_id

    @property
    def create_time(self):
        return self._create_time
    
    def dict_report(self):
        s = {
            "user_id" : str(self.user_id),
            "surname" : self.surname,
            "firstname" : self.firstname,
            "street" : self.street,
            "postcode" : self.postcode,
            "city" : self.city,
            "created:" : self.create_time,
            "connection_id:" : self.connection_id,
            "state" : self.state,
            "access_permitted" : self.access_permitted
        }
        return s

class AccessControlService(Resource):
    
    def __init__(self):
        pass

    def get(self, user_id = None):
        global USERS

        if user_id:
            if user_id in USERS:
                return USERS[user_id].dict_report()
            else:
                abort(404, message = "user id unknown")    
        return self.dict_user_list()
    
    def post(self):
        # Parse parameters
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', help='user id')
        parser.add_argument('surname', help='user surname')
        parser.add_argument('firstname', help='user firstname')
        parser.add_argument('street', help='user street and number')
        parser.add_argument('postcode', help='user postcode')
        parser.add_argument('city', help='user city')
        parser.add_argument('access_permitted', help='access permission (yes or no)')

        args = parser.parse_args()
        
        if (not args["user_id"] or 
            not args["surname"] or
            not args["firstname"] or 
            not args["street"] or
            not args["postcode"] or
            not args["city"] ):
            abort(400, message = "Missing or invalid parameters. Requires 'user_id', 'surname', 'firstname', 'street', 'postcode', 'city'")    
        else:
            user = User(args["user_id"], args["surname"],args["firstname"],args["street"],args["postcode"], args["city"])
            USERS[str(user.user_id)] = user

            return user.dict_report(), 201
    
    def put(self, user_id = None):
        
        if not user_id:
            abort(400, message = "Unknown User ID") 
        
        # Parse parameters
        parser = reqparse.RequestParser()
        parser.add_argument('surname', help='user surname')
        parser.add_argument('firstname', help='user firstname')
        parser.add_argument('street', help='user street')
        parser.add_argument('postcode', help='user postcode')
        parser.add_argument('city', help='user city')
        parser.add_argument('state', help="user state 'in' or 'out'")
        parser.add_argument('access_permitted', help='access permission')
        parser.add_argument('connection_id', help='client specific connection id (optional)')

        args = parser.parse_args()
        
        valid = True
        
        if user_id in USERS:
            if args["state"]:
                if args["state"].lower() != "in" and args["state"].lower() != "out":
                    abort(406, message = "state has to be 'in' or 'out' (in or out of the building)")
                    valid = False
                else:    
                    USERS[user_id].state = args["state"]
            
            if valid:
                if args["surname"]:
                    USERS[user_id].surname = args["surname"]
                
                if args["firstname"]:
                    USERS[user_id].firstname = args["firstname"]

                if args["street"]:
                    USERS[user_id].street = args["street"]

                if args["postcode"]:
                    USERS[user_id].postcode = args["postcode"]

                if args["city"]:
                    USERS[user_id].city = args["city"]

                if args["access_permitted"]:
                    USERS[user_id].access_permitted = args["access_permitted"]

                if args["connection_id"]:
                    USERS[user_id].connection_id = args["connection_id"]

            return USERS[user_id].dict_report()
        else:
            abort(400, message = "Unknown User ID") 

    def delete(self, user_id):
        if user_id:
            if user_id in USERS:
                del USERS[user_id]
            else:
                abort(404, message = "User id unknown")
                
        return self.dict_user_list()

    def dict_user_list(self):
        x = {
            "users" : [USERS[key].dict_report() for key in USERS]
        }
        return x

if __name__ == '__main__':
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(AccessControlService, '/V1.0/users', '/V1.0/users/' ,'/V1.0/users/<string:user_id>' )

    app.run(host = '0.0.0.0', port = 5900, debug=True)