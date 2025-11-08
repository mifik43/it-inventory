class Device:
    def __init__(self, id=None, name="", device_type="", serial_number="", 
                 mac_address="", ip_address="", location="", status="", 
                 assigned_to="", specifications="", created_at=None):
        self.id = id
        self.name = name
        self.type = device_type
        self.serial_number = serial_number
        self.mac_address = mac_address
        self.ip_address = ip_address
        self.location = location
        self.status = status
        self.assigned_to = assigned_to
        self.specifications = specifications
        self.created_at = created_at
    
    @staticmethod
    def from_row(row):
        return Device(
            id=row['id'],
            name=row['name'],
            device_type=row['type'],
            serial_number=row['serial_number'],
            mac_address=row['mac_address'],
            ip_address=row['ip_address'],
            location=row['location'],
            status=row['status'],
            assigned_to=row['assigned_to'],
            specifications=row['specifications'],
            created_at=row['created_at']
        )