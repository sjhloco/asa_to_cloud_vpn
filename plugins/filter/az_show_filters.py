class FilterModule(object):
    def filters(self):
        return {
            'check_az_show': self.check_az_show
        }

 # Check for whether vpn_conn is in the list of active ones got from azure
    def check_az_show(self, az_show, obj_name):
        if obj_name in az_show:
            return True
        else:
            return False