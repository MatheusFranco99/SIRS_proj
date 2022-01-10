
# RECEBE:

# do SNS quando user esta positivo pra covid19
# COD:<sns_code>:\n"

# de outro user quando muda de posicao
# LOC:<latitude>:<longitude>:\n

# de outro user quando percebe que esta proximo de si
# TOK:<mytoken>:\n

# de outro user em resposta a mensagem TOK enviada
# RTOK:<mytoken>:\n

# do server quando alguem tem covid
# CON:(<token>:)*\n


# ENVIA:

# Pra outros utilizadores: Sempre que altera a sua localizacao
# LOC:<latitude>:<longitude>:\n

# Pra outro utilizador: Sempre que recebe uma localizacao da qual esta proximo
# TOK:<mytoken>:\n

# Pra outro utilizador: Sempre que recebe "TOK:<token>:\n"
# RTOK:<mytoken>:\n


# Pro servidor: Sempre que recebe "COD:<sns_code>:\n" do sns
# POS:<sns_code>:(<encrypt_token>:)*\n



def listen():
    pass
    # get message
    # parse message
    # treat message
    # send response, if needed


def received_cod():
    pass

def received_loc():
    pass

def received_tok():
    pass

def received_rtok():
    pass

def received_con():
    pass



if __name__ == "__main__":

    # listen should run in background
    
    # wait in loop for command line inputs (as position shift)
        # send LOK in case of new position

    pass


