import sys
import time
import yaml
import pexpect
import getpass
import begin

ssh_connections = list()
connections = None

class Connection:
    def __init__(self, connection: dict):
        self.connection = connection
        self.server = self.connection['server']
        self.port = self.connection['port']
        if 'name' in self.connection:
            self.name = self.connection['name']
        else:
            self.name = '{}:{}'.format(self.server, self.port)

    def get_cmd(self):
        return self.__str__()

    def __str__(self):
        data_key = ''
        if 'public_key' in self.connection.keys():
            data_key = '-i {}'.format(self.connection['public_key'])

        data_tunnel = ''
        data_tunnels = list()

        if 'tunnels' not in self.connection.keys():
            print('Configuration error: ssh connection has no tunnels')
            return ''

        for tunnel in self.connection['tunnels']:
            t = tunnel.split(',')
            type = t[0]
            src_port = t[1]
            ip = t[2]
            dst_port = t[3]
            data_tunnels.append('-{} {}:{}:{}'.format(type, src_port, ip, dst_port))
        data_tunnel = ' '.join(data_tunnels)


        cmd = 'ssh -o IdentitiesOnly=yes {} {}@{} -p {} {}'.format(data_tunnel, self.connection['user'],
                                                                   self.connection['server'], self.connection['port'],
                                                                   data_key)

        return cmd



    def __repr__(self):
        return self.__str__()

def read_config(config_file: str) -> list:
    # El formato de fichero esperado con lineas con el siguiente estilo: local,puerto_origen,ip,puerto_destino

    with open(config_file, 'r') as f:
        data = yaml.load(f)

        connections = list()
        for c in data['connections']:
            conn = Connection(c)
            connections.append(conn)
        return connections

    raise FileNotFoundError('Config file not found: {}'.format(config_file))

def connect_ssh(connections: list) -> None:
    # Try to connect

    for c in connections:
        cmd = c.get_cmd()
        global ssh_connections
        ssh = pexpect.spawn(cmd)
        ssh_connections.append(ssh)

        try:
            time.sleep(0.1)
            # try:
            #     ssh.expect('(yes / no)?', timeout=0.2)
            #     time.sleep(0.1)
            #     ssh.sendline('yes')
            #     time.sleep(0.1)
            # except:
            #     pass

            ssh.expect('assword:', timeout=2)

            if not sys.stdin.isatty():
                ssh.sendline(sys.stdin.readline().rstrip())
            else:
                ssh.sendline(getpass.getpass('Insert password for {}: '.format(c.name)))

            time.sleep(0.5)
        except pexpect.TIMEOUT:
            # Excepcion por tiempo, porque se ha conectado al servidor ssh sin tener que meter la contraseña
            pass
        except pexpect.exceptions.EOF:
            pass

        print('    - {} connected'.format(c.name))

def sleep_loop():
    '''Bucle infinito hasta pulsar control c'''
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        sys.exit(0)

@begin.subcommand
def connectall():
    """Connect all ssh configured ssh connections"""
    print('Connecting all ssh connections')
    connect_ssh(connections)
    print('All connected')
    sleep_loop()

@begin.subcommand
def connect(names):
    """Connect given ssh connections"""
    names_list = names.split(',')
    print('Connecting {} connections'.format(names))
    connections_filtered = [c for c in connections if c.name in names_list]
    connect_ssh(connections_filtered)
    print('All connected')
    sleep_loop()

@begin.start(auto_convert=True)
def main(config_file: 'Config file' = 'tunnels.yaml'):
    """Create tunnels"""
    try:
        global connections
        connections = read_config(config_file)
    except FileNotFoundError:
        print('ERROR: File {} not found'.format(config_file))
        sys.exit(1)
