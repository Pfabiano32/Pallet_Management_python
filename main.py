# Standard Library
from datetime import datetime
import threading

# Third-party
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.factory import Factory
from kivy.graphics import Rectangle, Color, Line
from kivy.metrics import dp
from kivy.properties import (
    ListProperty, StringProperty, ObjectProperty, ColorProperty,
    NumericProperty, BooleanProperty, DictProperty
)
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

# Banco de Dados
from firebase_admin import credentials, firestore, initialize_app
from firebase_admin.firestore import FieldFilter


# Registre a fonte dos ícones sólidos
LabelBase.register(
    name="FontAwesome",  # Nome que você usará no KV
    fn_regular="fonts/fa-solid-900.otf"  # Caminho correto
)

## ---> CLASSES DE UI DE WIDGETS <--- ##
class CustomPopup(Popup):
    overlay_color = ListProperty([0, 0, 0, 0.7])
    title_color = ColorProperty(get_color_from_hex('#FFFFFF'))  # Cor do título branco
    border_color = ColorProperty(get_color_from_hex('#404040'))  # Cor da borda cinza escuro
    background_color = ColorProperty(get_color_from_hex('#808080'))  # Cor de fundo cinza médio
    BASE_SCREEN_RATIO = 0.6  # Referência
    MAX_SCALE = 0.8          # Redução máxima
    MIN_SCALE = 1.0        # Aumento mínimo

    def __init__(self, **kwargs):
        # super().__init__(**kwargs)
        self.original_size_hint = kwargs.get('size_hint', (0.7, 0.7))
        kwargs['size_hint'] = self.calculate_scaled_size_hint()
        super().__init__(**kwargs)
        self.separator_height = 0
        self.background = ''
        self.title_align = 'center'
        self.title_size = '20sp'

        # Atualiza ao redimensionar a janela
        Window.bind(on_resize=self.update_scale)

        # Configura o canvas
        with self.canvas.before:
            Color(rgba=self.background_color)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=self.border_color)
            self.border_line = Line(
                width=1, rectangle=[self.x, self.y, self.width, self.height])

        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def calculate_scaled_size_hint(self):
        if Window.width == 0:
            return self.original_size_hint

        scale_factor = (Window.width * self.BASE_SCREEN_RATIO) / Window.width
        scaled_w = self.original_size_hint[0] * \
            max(min(scale_factor, self.MAX_SCALE), self.MIN_SCALE)
        scaled_h = self.original_size_hint[1] * \
            max(min(scale_factor, self.MAX_SCALE), self.MIN_SCALE)
        return (scaled_w, scaled_h)

    def update_scale(self, instance, width, height):
        self.size_hint = self.calculate_scaled_size_hint()

    def update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.rectangle = [self.x, self.y, self.width, self.height]

    def on_dismiss(self):
        """Limpa os binds ao fechar"""
        Window.unbind(on_resize=self.update_scale)
        super().on_dismiss()


class RoundedButton(Button):
    base_color = ListProperty(get_color_from_hex('#42A5F5'))  # Cor padrão
    background_color = (0, 0, 0, 0)  # Desativa o fundo padrão
    background_normal = ''  # Remove o estilo padrão
    background_down = ''  # Remove o estilo de clique padrão
    min_width = NumericProperty(0)  # Nova propriedade
    min_height = NumericProperty(0)  # Opcional se quiser altura mínima


class RoundedTextInput(TextInput):
    cursor_color = ColorProperty(get_color_from_hex('#000000'))
    cursor_width = NumericProperty(dp(1))
    cursor_blink = BooleanProperty(True)
    show_cursor = BooleanProperty(False)
    foreground_color = ColorProperty(get_color_from_hex('#000000'))
    hint_text_color = ColorProperty(get_color_from_hex('#000000'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.blink_clock = None

    def on_focus(self, instance, value):
        if value:
            self.start_blink()
        else:
            self.stop_blink()

    def start_blink(self):
        self.show_cursor = True
        self.blink_clock = Clock.schedule_interval(
            lambda dt: setattr(self, 'show_cursor', not self.show_cursor),
            0.5  # Ajuste a velocidade do piscar aqui (0.5 segundos)
        )

    def stop_blink(self):
        if self.blink_clock:
            self.blink_clock.cancel()
        self.show_cursor = False


class RoundedSpinner(Spinner):
    base_color = ColorProperty(get_color_from_hex('#1565C0'))  # Cor base
    border_color = ColorProperty(get_color_from_hex('#0D47A1'))  # 70% da base_color
    background_color = ColorProperty((0, 0, 0, 0))  # Fundo transparente
    alert_color = ColorProperty(get_color_from_hex('#FFCDD2'))  # Cor pré-definida
    radius = ListProperty([dp(15)])
    clicked = BooleanProperty(False)
    option_font_size = NumericProperty('18sp')  # Nova propriedade customizada
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Configuração correta do dropdown
        self.dropdown_cls = Factory.DropDown
        self.option_cls = Factory.get('SpinnerOption')  # Usa a definição do KV
        self.bind(option_font_size=self.atualizar_opcoes)

    def atualizar_opcoes(self, instance, value):
        """Atualiza o tamanho da fonte das opções"""
        self.option_cls.font_size = value

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.clicked = True  # Marca que foi clicado
        return super().on_touch_down(touch)


class FirebaseManager:
    _instance = None

    def __init__(self):
        if not FirebaseManager._instance:
            try:
                self.cred = credentials.Certificate("serviceAccountKey.json")
                self.app = initialize_app(self.cred, {
                    'databaseURL': 'https://registrados-de-pallets.firebaseio.com',  # Exemplo
                    'projectId': 'registrados-de-pallets'  # ID do seu projeto
                })
                self.db = firestore.client()
                FirebaseManager._instance = self
                print("✅ Firebase inicializado com sucesso!")
            except FileNotFoundError:
                print("❌ ERRO: Arquivo 'serviceAccountKey.json' não encontrado.")
                raise
            except Exception as e:
                print(f"❌ Erro crítico no Firebase: {str(e)}")
                raise

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = FirebaseManager()
        return cls._instance

    def get_user_id(self):
        return "user_id_temporario"


class ClientManager(EventDispatcher):
    clientes = DictProperty({})
    __events__ = ('on_clientes',)

    def __init__(self):
        super().__init__()
        try:
            self.firebase = FirebaseManager.get_instance()
            self.db = self.firebase.db
            self.user_id = self.firebase.get_user_id()
            self.clientes = self.carregar_clientes()  # Carrega clientes aqui

        except Exception as e:
            print(f"Falha ao criar ClientManager: {str(e)}")
            raise

    def carregar_clientes(self):
        """Carrega todos os clientes (visíveis para todos)"""
        try:
            docs = self.db.collection('clientes').stream()
            clientes_dict = {}
            for doc in docs:
                dados = doc.to_dict()
                pallets = dados.get('pallets', [])
                pallets_ordenados = sorted(pallets)  # Ordem alfabética
                clientes_dict[doc.id] = {
                    'pallets': pallets_ordenados,  # Lista ordenada
                    'criado_por': dados.get('criado_por', '')
                }
            
            return clientes_dict
        except Exception as e:
            print(f"Erro ao carregar clientes: {e}")
            return {}

    def adicionar_cliente(self, nome_cliente):
        """Adiciona novo cliente visível para todos"""
        try:
            cliente_ref = self.db.collection('clientes').document(nome_cliente)
            if not cliente_ref.get().exists:
                cliente_ref.set({
                    'pallets': [],
                    'criado_por': self.user_id
                })
                
                self.atualizar_lista_clientes()  # Atualiza a lista local
                return True
            return False

        except Exception as e:
            print(f"Erro ao adicionar cliente: {e}")
            return False

    def adicionar_pallet(self, cliente, pallet):
        """Qualquer usuário pode adicionar pallet a cliente existente"""
        try:
            cliente_ref = self.db.collection('clientes').document(cliente)
            if cliente_ref.get().exists:
                cliente_ref.update({
                    'pallets': firestore.ArrayUnion([pallet])
                })
                return True
            return False
        except Exception as e:
            print(f"Erro ao adicionar pallet: {e}")
            return False

    def editar_cliente(self, cliente_antigo, cliente_novo):
        """Edita nome do cliente e atualiza todos os registros relacionados"""
        try:
            # 1. Verifica permissão primeiro
            cliente_ref = self.db.collection(
                'clientes').document(cliente_antigo)
            doc = cliente_ref.get()

            if not doc.exists:
                print("Cliente antigo não encontrado!")
                return False

            dados = doc.to_dict()

            # 1. Verifica permissão primeiro
            if dados.get('criado_por') != self.user_id:
                print("Apenas o criador pode editar este cliente!")
                return False

            # 3. Verifica se o novo nome já existe
            novo_ref = self.db.collection('clientes').document(cliente_novo)
            if novo_ref.get().exists:
                print("Já existe um cliente com este novo nome!")
                return False

            # 4. Atualiza registros relacionados usando a sintaxe correta
            registros_ref = self.db.collection('registros')
            query = registros_ref.where(filter=FieldFilter('cliente', '==', cliente_antigo))
            docs = query.stream()

            batch = self.db.batch()
            registros_para_atualizar = []

            for doc in docs:
                doc_ref = registros_ref.document(doc.id)
                batch.update(doc_ref, {'cliente': cliente_novo})
                registros_para_atualizar.append(doc_ref)

            # 5. Cria novo documento e deleta o antigo
            novo_ref = self.db.collection('clientes').document(cliente_novo)
            novo_ref.set(dados)
            cliente_ref.delete()

            # 6. Executa o batch se houver registros
            if registros_para_atualizar:
                batch.commit()

            # 6. Atualiza a lista local e notifica a interface
            self.atualizar_lista_clientes()
            return True

        except Exception as e:
            print(f"Erro ao editar cliente: {e}")
            try:
                # Rollback mais detalhado
                if 'novo_ref' in locals():
                    if novo_ref.get().exists:
                        print("Revertendo criação do novo cliente...")
                        novo_ref.delete()

                if 'cliente_ref' in locals():
                    if not cliente_ref.get().exists and 'dados' in locals():
                        print("Restaurando cliente original...")
                        cliente_ref.set(dados)

            except Exception as rollback_error:
                print(f"Erro durante rollback: {rollback_error}")
            return False

    def remover_cliente(self, cliente):
        """Remove cliente (apenas criador pode remover)"""
        try:
            cliente_ref = self.db.collection('clientes').document(cliente)
            dados = cliente_ref.get().to_dict()

            if dados.get('criado_por') != self.user_id:
                print("Apenas o criador pode remover este cliente!")
                return False

            cliente_ref.delete()
            self.atualizar_lista_clientes()
            return True

        except Exception as e:
            print(f"Erro ao remover cliente: {e}")
            return False

    def remover_pallet(self, cliente, pallet):
        """Remove pallet (apenas criador do cliente pode remover)"""
        try:
            cliente_ref = self.db.collection('clientes').document(cliente)
            dados = cliente_ref.get().to_dict()

            if dados.get('criado_por') != self.user_id:
                print("Apenas o criador pode remover pallets!")
                return False

            cliente_ref.update({
                'pallets': firestore.ArrayRemove([pallet])
            })
            return True

        except Exception as e:
            print(f"Erro ao remover pallet: {e}")
            return False

    def atualizar_lista_clientes(self):
        """Recarrega os clientes do Firebase e notifica a interface"""
        try:
            self.clientes = self.carregar_clientes()
            self.dispatch('on_clientes')
        except Exception as e:
            print(f"Erro ao atualizar clientes: {e}")

    def on_clientes(self, *args):
        """Handler para evento de atualização"""
        pass


class EditablePalletItem(BoxLayout):
    pallet = StringProperty('')
    pallet_original = StringProperty('')
    cliente = StringProperty('')
    editando = BooleanProperty(False)
    client_manager = ObjectProperty(None)
    marcado_exclusao = BooleanProperty(False)
    excluido = BooleanProperty(False)

    def __init__(self, client_manager, pallet, **kwargs):
        super().__init__(**kwargs)
        self.client_manager = client_manager
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(50)
        self.pallet_original = pallet
        self.pallet = pallet
        self.input_pallet = None
        self.atualizar_visualizacao()
        self.bind(editando=self.atualizar_visualizacao)
        self.bind(excluido=self.on_excluido)
        self.bind(marcado_exclusao=self.atualizar_estilo)  # Novo bind
        self.bind(excluido=self.on_excluido)

    def atualizar_visualizacao(self, *args):
        self.clear_widgets()

        if self.editando:
            self.input_pallet = RoundedTextInput(
                text=self.pallet,
                size_hint_x=0.6
            )
            self.input_pallet.bind(text=self.atualizar_pallet_local)
            self.add_widget(self.input_pallet)
        else:
            lbl = Label(
                text=self.pallet,
                size_hint_x=0.6,
                halign='left',
                color=get_color_from_hex('#000000')
            )
            btn_editar = Button(
                text='\uf304',  # Ícone de edição
                font_name="FontAwesome",
                font_size='24sp',  # Tamanho aumentado
                size_hint_x=0.2,
                background_color=(0, 0, 0, 0),  # Fundo transparente
                color=get_color_from_hex('#000000'),  # Azul claro
                background_normal='',  # Remove o estilo padrão
                on_press=lambda x: setattr(self, 'editando', True)
            )
            self.add_widget(lbl)
            self.add_widget(btn_editar)

        btn_excluir = Button(
            text='\uf00d',  # Ícone de exclusão
            font_name="FontAwesome",
            font_size='24sp',  # Tamanho aumentado
            size_hint_x=0.2,
            background_color=(0, 0, 0, 0),  # Fundo transparente
            color = get_color_from_hex('#000000'),  # Azul escuro
            background_normal = '',  # Remove o estilo padrão
            on_press = self.excluir_pallet
        )
        self.add_widget(btn_excluir)
    
    def atualizar_pallet_local(self, instance, value):
        """Atualiza o valor local quando o texto muda"""
        self.pallet = value

    def atualizar_estilo(self, instance, value):
        # Altera a cor de fundo se marcado para exclusão
        if value:
            self.canvas.before.clear()
            with self.canvas.before:
                Color(rgba=get_color_from_hex('#FFEBEE'))  # Vermelho mais suave
                Rectangle(pos=self.pos, size=self.size)
        else:
            self.canvas.before.clear()
            with self.canvas.before:
                Color(rgba=(1, 1, 1, 1))  # Branco
                Rectangle(pos=self.pos, size=self.size)
    
    def on_excluido(self, instance, value):
        if value and self.parent is not None:
            try:
                self.parent.remove_widget(self)
            except AttributeError:
                pass

    def excluir_pallet(self, instance):
        # Alterar para marcar o nome original para exclusão
        self.marcado_exclusao = not self.marcado_exclusao
        if self.marcado_exclusao:
            self.pallet_original = self.pallet  # Mantém o original para exclusão

# ---> CLASSE DA ABA LATERAL <--- #
class Sidebar(FloatLayout):
    client_manager = ObjectProperty(None)
    tela_pai = ObjectProperty(None)
    pallets_marcados = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_pai = None
        self.client_manager = App.get_running_app().client_manager
        self.pallets_marcados = []  # Lista para guardar pallets marcados

    def abrir_popup_registro(self):
        content = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=[dp(20), dp(10), dp(10), dp(10)]
        )
        
        # Input do Cliente
        self.input_cliente = RoundedTextInput(hint_text="Nome do Cliente", size_hint_y=None, height=dp(60))
        content.add_widget(self.input_cliente)

        # Container de Pallets com Scroll
        scroll_pallets = ScrollView(size_hint=(1, 1))
        self.pallets_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(10))

        self.pallets_container.bind(minimum_height=self.pallets_container.setter('height'))
        scroll_pallets.add_widget(self.pallets_container)
        content.add_widget(scroll_pallets)

        btn_layout_mais = AnchorLayout(
            size_hint_y=None, 
            height=dp(50), 
            anchor_x='left',  # Alinha todo o conteúdo à esquerda
            padding=[dp(20), 0, 0, 0]  # Padding esquerdo
)

        # Botão para adicionar novos inputs
        btn_mais = RoundedButton(
            text="[font=FontAwesome]\uf067[/font] Pallet",
            markup=True,
            font_size = '22sp',  # Tamanho do texto normal
            size_hint = (None, None), # Desativa o comportamento automático de dimensionamento
            size = (dp(110), dp(50)),  # Aumentei a altura para 50dp e largura para 110dp
            base_color = get_color_from_hex('#1565C0'),  # Azul escuro
            color = get_color_from_hex('#FFFFFF'),
            halign = 'left',  #  Alinhamento à esquerda
            text_size = (dp(130), None),
            padding = (dp(15), 0),
            pos_hint = {'x': 0},  # Cola na esquerda do container
            on_press = lambda x: self.adicionar_input_pallet())

        # Layout principal
        btn_layout_mais.add_widget(btn_mais)
        content.add_widget(btn_layout_mais)

        content.add_widget(Widget(size_hint_y=None, height=dp(5)))

        # Botões de ação
        btn_container = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(20)
        )
        
        btn_salvar = RoundedButton(
            text = "Salvar",
            font_size = '26sp',  # Font do texto
            on_press = lambda x: self.salvar_registro(popup)
        )

        btn_cancelar = RoundedButton(
            text = "Cancelar",
            font_size = '26sp',  # Font do texto
            on_press = lambda x: popup.dismiss()
        )

        btn_container.add_widget(btn_salvar)
        btn_container.add_widget(btn_cancelar)
        content.add_widget(btn_container)

        self.adicionar_input_pallet()

        popup = CustomPopup(
            title="Registrar Novo Cliente/Pallet",
            content=content,
            size_hint=(0.55, 0.60)
        )

        btn_salvar.bind(on_press=lambda x: self.salvar_registro(popup))
        btn_cancelar.bind(on_press=popup.dismiss)

        popup.open()

    def adicionar_input_pallet(self):
        novo_input = RoundedTextInput(
            hint_text="Nome do Pallet",
            size_hint_y=None,
            height=dp(50)
        )
        self.pallets_container.add_widget(novo_input)

    def salvar_registro(self, popup):
        cliente = self.input_cliente.text.strip()
        pallets = [
            input.text.strip()
            for input in self.pallets_container.children
            if input.text.strip()
        ]

        if cliente and pallets:
            try:
                success = self.client_manager.adicionar_cliente(cliente)
                if not success:
                    return

                    # Adiciona pallets de forma assíncrona
                def adicionar_pallets(_):
                    try:
                        for pallet in pallets:
                            self.client_manager.adicionar_pallet(cliente, pallet)
                    
                        Clock.schedule_once(lambda dt: self.finalizar_registro(popup))
                
                    except Exception as e:
                        pass

                threading.Thread(target=adicionar_pallets, args=(None,)).start()

            except Exception as e:
                pass
        else:
            pass

    def finalizar_registro(self, popup):
        try:
            # Atualiza dados locais
            self.client_manager.atualizar_lista_clientes()
        
            # Atualiza UI
            self.atualizar_interface_pai()
            Clock.schedule_once(lambda dt: self.atualizar_todos_spinners())

            # Fecha popup só depois de tudo atualizado
            popup.dismiss()
        
        except Exception as e:
            pass

    def atualizar_todos_spinners(self):
        app = App.get_running_app()
    
        # Atualiza Spinner na TelaRegistro
        tela_registro = app.root.get_screen('registro')
        tela_registro.ids.cliente_spinner.values = list(self.client_manager.clientes.keys())
    
        # Atualiza Spinner na TelaSaida
        tela_saida = app.root.get_screen('saida')
        tela_saida.ids.cliente_spinner_saida.values = list(self.client_manager.clientes.keys())
    
    def atualizar_interface_pai(self):
        try:
            # Atualiza dados locais primeiro
            self.client_manager.atualizar_lista_clientes()
        
            # Atualiza a tela de registro
            app = App.get_running_app()
            tela_registro = app.root.get_screen('registro')
        
            # Força atualização dos componentes
            tela_registro.ids.cliente_spinner.values = list(self.client_manager.clientes.keys())
            tela_registro.ids.cliente_spinner.text = "Selecione um Cliente"
            tela_registro.atualizar_pallets()
        
        except Exception as e:
            print(f"Erro ao atualizar interface: {str(e)}")

    # ---> POPUP DE EDIÇÃO <--- #
    def abrir_popup_edicao(self):
        # Define um valor de padding de acordo com a altura da tela
        if Window.height < 600:
            top_padding = dp(40)  # Telas pequenas
        else:
            top_padding = dp(10)  # Telas maiores

       # Layout principal
        content = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=[dp(10), top_padding, dp(15), dp(20)]
        )

        # Faz com que o layout se ajuste à altura mínima necessária dos seus filhos
        content.bind(minimum_height=content.setter('height'))
        
        def carregar_pallets(instance, value):
            cliente = spinner_clientes.text
            if cliente in self.client_manager.clientes:
                self.lista_pallets.clear_widgets()
                pallets = sorted(self.client_manager.clientes[cliente]['pallets'])  # Ordena os pallets
                for pallet in pallets:
                    item = EditablePalletItem(
                        client_manager=self.client_manager,
                        pallet = pallet,
                        cliente = cliente
                    )
                    # Adicione bind para atualização contínua
                    item.marcado_exclusao = pallet in self.pallets_marcados
                    self.lista_pallets.add_widget(item)

        has_clients = bool(self.client_manager.clientes)
        
        # Crie um container para spinner e aviso
        header_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(40),  # Altura total fixa para header
            spacing=dp(2)
        )

        # Spinner para seleção de cliente
        spinner_clientes = RoundedSpinner(
            text = "Selecione um cliente",  # Texto fixo inicial
            values = list(self.client_manager.clientes.keys())
            if has_clients else [],  # Lista vazia se não houver
            font_size ='20sp',
            option_font_size ='18sp',  # Define o tamanho das opções
            size_hint = (1, None),
            height = dp(38),
            padding = [0, dp(10)],
        )

        if not has_clients:
            # ✅ Usa o valor da instância
            spinner_clientes.background_color = spinner_clientes.alert_color
            spinner_clientes.color = get_color_from_hex('#B71C1C')
        else:
            spinner_clientes.background_color = (0, 0, 0, 0)

        spinner_clientes.bind(text=carregar_pallets)

        # Label de aviso (inicialmente invisível)
        lbl_aviso = Label(
            text="[color=#D32F2F]\uf071[/color] Nenhum cliente cadastrado!",
            markup=True,
            font_size='14sp',
            size_hint_y=None,
            height=dp(30),
            opacity=0  # Inicia oculto
        )

        header_container.add_widget(lbl_aviso)
        header_container.add_widget(spinner_clientes)
        content.add_widget(header_container)
        # Adicione um espaço abaixo do spinner (10dp)
        content.add_widget(Widget(size_hint_y=None, height=dp(10)))  # Espaçamento

        # Função de callback
        def on_spinner_click(instance, value):
            if not instance.values:  # Só mostra se não houver clientes
                lbl_aviso.opacity = 1
                instance.background_color = instance.alert_color
                instance.color = get_color_from_hex('#B71C1C')
                instance.text = "Nenhum cliente cadastrado"  # Muda o texto após clique
            else:
                lbl_aviso.opacity = 0

        spinner_clientes.bind(clicked=on_spinner_click)  # Vincula ao clique
        
        # Layout principal em duas colunas
        main_columns = BoxLayout(
            orientation='horizontal',
            spacing=dp(20),
            padding=dp(5),
            size_hint = (1, 1)  # Expande para ocupar todo espaço vertical restante
        )

        # Coluna esquerda (inputs)
        input_column = BoxLayout(
            orientation='vertical',
            size_hint=(0.4, 1),
            spacing=dp(10)
        )

        # Coluna direita (pallets)
        list_column = BoxLayout(
            orientation='vertical',
            size_hint=(0.6, 1),
            spacing=dp(10)
        )

        # Campos de edição
        input_novo_nome = RoundedTextInput(
            hint_text="Novo Nome do Cliente",
            size_hint=(1, None),
            height=dp(50),
            font_size='16sp'
        )

        input_novo_pallet = RoundedTextInput(
            hint_text="Novo Pallet",
            size_hint=(1, None),
            height=dp(50),
            font_size='16sp'
        )

        scroll_pallets = ScrollView(
            size_hint=(1, 1),
            bar_width=dp(10)
        )
        
        self.lista_pallets = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(10),
        )

        self.lista_pallets.bind(minimum_height=self.lista_pallets.setter('height'))
        scroll_pallets.add_widget(self.lista_pallets)

        # Adicione os inputs na coluna da esquerda
        input_column.add_widget(Label(text = 'Editar Cliente:', font_size='20sp', size_hint_y=None, height=dp(30)))
        input_column.add_widget(input_novo_nome)
        input_column.add_widget(input_novo_pallet)
        input_column.add_widget(Widget(size_hint_y=1))  # Preenche espaço restante

        # Adicione a lista na coluna da direita
        list_column.add_widget(Label(text = 'Pallets:', font_size='20sp', size_hint_y=None, height=dp(30)))
        list_column.add_widget(scroll_pallets)

        # Junte as colunas
        main_columns.add_widget(input_column)
        main_columns.add_widget(list_column)

        # Adicione ao conteúdo principal
        content.add_widget(main_columns)

        layout_botoes = BoxLayout(
            orientation='vertical',
            spacing=dp(25),
        )
        # Botões
        btn_salvar = RoundedButton(
            text="Salvar Alterações",
            size_hint_y=None,
            height=dp(50)
        )

        # Layout para os botões inferiores
        botoes_inferiores = BoxLayout(
            orientation = 'horizontal',
            spacing = dp(20),  # Espaçamento entre widgets
            size_hint_y = None,
            height = dp(60)
        )

        btn_excluir = RoundedButton(
            text = "Excluir",
            size_hint_x = 0.25,
            min_width = dp(250),
            height = dp(30),
            base_color = get_color_from_hex('#D32F2F'))

        btn_cancelar = RoundedButton(
            text = "Cancelar",
            size_hint_x = 0.45,
            min_width = dp(305),
            height = dp(30),
            base_color = get_color_from_hex('#616161'))

        botoes_inferiores.add_widget(btn_excluir)
        botoes_inferiores.add_widget(btn_cancelar)
        layout_botoes.add_widget(btn_salvar)
        layout_botoes.add_widget(botoes_inferiores)

        content.add_widget(layout_botoes)

        # Posiciona os botões manualmente
        btn_excluir.pos_hint = {'x': 0, 'center_y': 0.5}
        btn_cancelar.pos_hint = {'right': 1, 'center_y': 0.5}

        def atualizar_largura_botoes(instance, value):
            btn_excluir.width = max(instance.width * 0.45, dp(250))
            btn_cancelar.width = max(instance.width * 0.45, dp(250))

        botoes_inferiores.bind(width=atualizar_largura_botoes)
        atualizar_largura_botoes(botoes_inferiores, None)

        popup = CustomPopup(
            title="Editar Cliente/Pallet",
            content = content,
            size_hint = (0.6, 0.75)
        )

        self.lista_pallets.client_manager = self.client_manager
        spinner_clientes.values = list(self.client_manager.clientes.keys())  # Atualiza valores

        def salvar_alteracoes(instance):
            if not spinner_clientes.text or spinner_clientes.text == "Selecione um Cliente":
                self.mostrar_erro("Selecione um cliente válido!")
                return

            # 1. Editar nome do cliente
            client_manager = self.client_manager
            cliente_antigo = spinner_clientes.text
            novo_nome_cliente = input_novo_nome.text.strip()

            try:
                # 2. Processar edição do nome do cliente
                if novo_nome_cliente and novo_nome_cliente != cliente_antigo:
                    if not client_manager.editar_cliente(cliente_antigo, novo_nome_cliente):
                        return

                # 3. Processar exclusões de pallets marcados
                cliente_atual = novo_nome_cliente if novo_nome_cliente else cliente_antigo
                
                # 4. Processar edições de nomes de pallets
                pallets_para_atualizar = []
                for item in self.lista_pallets.children:
                    if isinstance(item, EditablePalletItem) and item.editando:
                        novo_nome = item.pallet.strip()  # Pega o valor atualizado
                        if novo_nome and novo_nome != item.pallet_original:
                            pallets_para_atualizar.append((
                            item.pallet_original,  # Nome antigo
                        novo_nome              # Nome novo
                    ))
                
                # 5. Atualizar pallets no Firebase
                for antigo, novo in pallets_para_atualizar:
                    client_manager.remover_pallet(cliente_atual, antigo)
                    client_manager.adicionar_pallet(cliente_atual, novo)

                pallets_para_excluir = [
                    item.pallet for item in self.lista_pallets.children 
                    if isinstance(item, EditablePalletItem) and item.marcado_exclusao
                ]
                
                for pallet in pallets_para_excluir:
                    client_manager.remover_pallet(cliente_atual, pallet)

                # 6. Adicionar novo pallet
                novo_pallet = input_novo_pallet.text.strip()
                if novo_pallet:
                    client_manager.adicionar_pallet(cliente_atual, novo_pallet)

                    # 7. Forçar atualização global
                Clock.schedule_once(lambda dt: [
                    client_manager.atualizar_lista_clientes(),
                    self.atualizar_interface(),
                    setattr(spinner_clientes, 'values', list(client_manager.clientes.keys()))
                ])
        
                client_manager.atualizar_lista_clientes()
                input_novo_pallet.text = ''
                self.pallets_marcados = []  # Limpa os marcadores
                self.atualizar_interface()
                popup.dismiss()

            except Exception as e:
                print(f"Erro ao salvar alterações: {e}")
                self.mostrar_erro("Erro ao salvar alterações!")

        def excluir_registro(instance):
            cliente = spinner_clientes.text
            self.client_manager.remover_cliente(cliente)
            popup.dismiss()
            self.atualizar_interface()

        # --- CONFIGURAÇÃO FINAL ---
        btn_salvar.bind(on_press=salvar_alteracoes)
        btn_excluir.bind(on_press=excluir_registro)
        btn_cancelar.bind(on_press=popup.dismiss)

        popup.open()
    
    # Novo método para guardar os pallets marcados
    def on_pallet_marcado(self, instance, value):
        pallet = instance.pallet
        if value and pallet not in self.pallets_marcados:
            self.pallets_marcados.append(pallet)
        elif not value and pallet in self.pallets_marcados:
            self.pallets_marcados.remove(pallet)

    def atualizar_interface(self, instance=None, value=None):
        """Força atualização completa da interface"""
        try:
            app = App.get_running_app()
            # Atualiza dados locais e Firebase
            app.client_manager.atualizar_lista_clientes()
            
            telas = {
                'registro': 'cliente_spinner', 
                'saida': 'cliente_spinner_saida'
            }

            for screen_name, spinner_id in telas.items():
                tela = app.root.get_screen(screen_name)
                if hasattr(tela, 'ids') and spinner_id in tela.ids:
                    spinner = tela.ids[spinner_id]
                    spinner.values = list(app.client_manager.clientes.keys())  # Convertemos para lista
        
            # Atualiza o próprio popup (se existir)
            if hasattr(self, 'lista_pallets'):
                self.lista_pallets.clear_widgets()
                if app.client_manager.clientes:
                    clientes_lista = list(app.client_manager.clientes.keys())
                    if clientes_lista:
                        cliente = clientes_lista[0]
                        # Ordenar os pallets
                        pallets = sorted(app.client_manager.clientes[cliente]['pallets'])
                        for pallet in pallets:
                            item = EditablePalletItem(
                                client_manager=app.client_manager,
                                pallet=pallet,
                                cliente=cliente
                            )
                            # Restaura o estado de marcação
                            if pallet in self.pallets_marcados:
                                item.marcado_exclusao = True
                            item.bind(marcado_exclusao=self.on_pallet_marcado)
                            self.lista_pallets.add_widget(item)

        except Exception as e:
            print(f"Erro na atualização: {str(e)}")


class BaseScreen(Screen):
    def toggle_sidebar(self):
        self.sidebar = Sidebar(
            client_manager=App.get_running_app().client_manager,
            tela_pai=self
        )
        self.popup = Popup(
            title='',
            content=self.sidebar,
            size_hint=(0.45, 1),
            pos_hint={'x': 0, 'top': 1}
        )
        self.sidebar.popup_pai = self.popup
        self.popup.open()


# ---> TELAS DO APLICATIVO <--- #
class TelaInicial(Screen):
    pass


class TelaRegistro(BaseScreen):
    registro_pallets = ListProperty([])
    client_manager = ObjectProperty(None)  # Adicione isso

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_manager = App.get_running_app().client_manager
        self.client_manager.bind(clientes=self.atualizar_pallets)
        self.client_manager.bind(clientes=lambda inst, val: self.atualizar_spinners())
        self.carregar_dados()

    def voltar_para_registro(self):
        if hasattr(self, 'popup') and self.popup:
            self.popup.dismiss()
    
    def atualizar_interface(self):
        """Atualiza a lista de clientes e pallets"""
        self.client_manager.atualizar_lista_clientes()
        self.atualizar_pallets()
        self.ids.cliente_spinner.values = list(self.client_manager.clientes.keys())
    
    def atualizar_spinners(self):
        """Atualiza os valores do spinner dinamicamente"""
        self.ids.cliente_spinner.values = list(self.client_manager.clientes.keys())

    def atualizar_pallets(self, *args):
        cliente = self.ids.cliente_spinner.text
        if cliente not in self.client_manager.clientes:
            return

        pallets = self.client_manager.clientes[cliente]['pallets']

        # Limpa todos os pallets existentes
        self.ids.pallets_container.clear_widgets()

        # Adiciona uma linha para cada pallet do cliente
        for pallet in pallets:
            linha = BoxLayout(
                orientation='horizontal',
                size_hint=(1, None),
                height=dp(70),
                padding=dp(10),
                spacing=dp(15))

            # Label com nome do pallet
            lbl_pallet = Label(
                text = pallet,
                size_hint_x = 0.4,
                color = get_color_from_hex('#000000'),
                font_size = '16sp')

            # Input de quantidade
            input_quantidade = RoundedTextInput(
                hint_text = "Quantidade",
                size_hint_x = 0.4,
                size_hint_y = None,
                height = dp(50))

            linha.add_widget(lbl_pallet)
            linha.add_widget(input_quantidade)
            self.ids.pallets_container.add_widget(linha)

    def carregar_dados(self):
        # Remova toda a lógica do Excel
        self.registro_pallets = []  # Dados virão do Firebase
    
    def on_pre_enter(self):
        # Preenche a data automaticamente ao entrar na tela
        super().on_pre_enter()
        self.ids.data_input.text = datetime.now().strftime("%d/%m/%Y")

    def registrar_pallets(self):
        data = self.ids.data_input.text.strip()
        cliente = self.ids.cliente_spinner.text

        # Conexão com o Firebase
        db = FirebaseManager.get_instance().db
        registros_ref = db.collection('registros')

        # Lista para armazenar erros
        erros = []

        # Processa cada registro
        for child in self.ids.pallets_container.children:
            if isinstance(child, BoxLayout):
                # Encontra os componentes na linha
                lbl_pallet = None
                input_quantidade = None

                for widget in child.children:
                    if isinstance(widget, Label):
                        lbl_pallet = widget
                    elif isinstance(widget, RoundedTextInput):
                        input_quantidade = widget

                # Valida e coleta os dados
                if lbl_pallet and input_quantidade:
                    quantidade = input_quantidade.text.strip()

                    if not quantidade:
                        erros.append(
                            f"Quantidade não informada para {lbl_pallet.text}")
                        continue

                    if not quantidade.isdigit():
                        erros.append(
                            f"Quantidade inválida para {lbl_pallet.text}")
                        continue

                    try:
                        # Adiciona registro no Firebase
                        registros_ref.add({
                            'cliente': cliente,
                            'pallet': lbl_pallet.text,
                            'quantidade': int(quantidade),
                            'data': data,
                            'timestamp': firestore.SERVER_TIMESTAMP
                        })
                    except Exception as e:
                        erros.append(
                            f"Erro ao salvar {lbl_pallet.text}: {str(e)}")

        # Feedback ao usuário
        if erros:
            self.mostrar_popup("Erros", "\n".join(erros))
        else:
            self.mostrar_popup("Sucesso", "Registros salvos com sucesso!")
            self.voltar_menu()

    def voltar_menu(self):
        self.ids.cliente_spinner.text = "Selecione um Cliente"
        self.ids.pallets_container.clear_widgets()
        self.ids.data_input.text = ""

    def mostrar_popup(self, titulo, mensagem):
        from kivy.uix.popup import Popup
        content = BoxLayout(orientation='vertical', padding=10)

        # Mensagem
        lbl_mensagem = Label(
            text=mensagem,
            font_size=24,
            color=get_color_from_hex('#000000'),
            halign='center'
        )
        content.add_widget(lbl_mensagem)

        # Container para o botão (FloatLayout)
        btn_container = FloatLayout(
            size_hint_y=None, 
            height=dp(60)
        )

        # Botão "OK" no canto inferior direito
        btn_ok = Button(
            text="OK",
            size_hint=(None, None),
            size=(dp(120), dp(40)),
            pos_hint={'right': 1, 'y': 0},
            background_color=get_color_from_hex('#2E7D32'),
            color=get_color_from_hex('#FFFFFF'),
            background_normal=''
        )
        btn_container.add_widget(btn_ok)
        # 🔑 Adiciona o container ao conteúdo!
        content.add_widget(btn_container)

        # Popup
        popup = Popup(
            title=titulo,
            content=content,
            size_hint=(0.7, 0.4),
            separator_height=0,
            background_color=get_color_from_hex('#FFFFFF'),
            title_color=get_color_from_hex('#000000'),
            title_size='26sp',
            title_align='center'
        )

        btn_ok.bind(on_press=popup.dismiss)
        popup.open()


class TelaSaida(BaseScreen):
    client_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_manager = App.get_running_app().client_manager
        self.client_manager.bind(clientes=self.atualizar_pallets)
        self.client_manager.bind(clientes=lambda inst, val: self.atualizar_spinners())
        self.carregar_dados()

    def carregar_dados(self):
        self.registro_saidas = []
    
    def atualizar_spinners(self):
        """Atualiza os valores do spinner dinamicamente"""
        self.ids.cliente_spinner_saida.values = list(self.client_manager.clientes.keys())

    def atualizar_pallets(self, *args):
        cliente = self.ids.cliente_spinner_saida.text

        if cliente == "Selecione um Cliente":
            return  # Não faz nada se nenhum cliente estiver selecionado
        
        if cliente not in self.client_manager.clientes:
            self.ids.pallets_container_saida.clear_widgets()
            return

        # Obtém a lista de pallets do cliente (igual à TelaRegistro)
        pallets = self.client_manager.clientes[cliente].get('pallets', [])

        # Agendando a atualização da UI para o próximo frame
        Clock.schedule_once(lambda dt: self._atualizar_ui(pallets))

    def _atualizar_ui(self, pallets):
        self.ids.pallets_container_saida.clear_widgets()
        cliente = self.ids.cliente_spinner_saida.text
        totais = self.obter_totais_cliente(cliente)

        for pallet in pallets:
            total = totais.get(pallet, 0)
            # Criação da lista de pallets
            linha = BoxLayout(
                orientation='horizontal',
                size_hint=(1, None),
                height=dp(70),
                spacing=dp(10)
            )

            lbl_pallet = Label(
                text = pallet,
                font_size = '16sp',
                size_hint_x = 0.4,
                halign = 'left',
                color = get_color_from_hex('#000000'), 
            )

            lbl_total = Label(
                text = f"Total: {total}",
                font_size = '16sp',
                size_hint_x = 0.4,
                halign = 'left',
                color = get_color_from_hex('#2E7D32'))  # Cor verde para destaque
        
            input_saida = RoundedTextInput(
                hint_text = "Qtde. Saída",
                size_hint_x = 0.4,
                input_filter = 'int',
                size_hint_y = None,
                height = dp(50)
            )

            linha.add_widget(lbl_pallet)
            linha.add_widget(lbl_total)
            linha.add_widget(input_saida)
            self.ids.pallets_container_saida.add_widget(linha)

        # Atualizações necessárias para o Kivy renderizar corretamente
        self.ids.pallets_container_saida.height = self.ids.pallets_container_saida.minimum_height
        self.ids.pallets_container_saida.do_layout()

    def obter_totais_cliente(self, cliente):
        try:
            cliente_info = self.client_manager.clientes.get(cliente, {})
            pallets_cliente = cliente_info.get('pallets', [])

            # Inicializa todos os pallets com total 0
            totais = {pallet: 0 for pallet in pallets_cliente}

            # Busca registros e soma as quantidades
            db = FirebaseManager.get_instance().db
            registros_ref = db.collection('registros')
            query = registros_ref.where(filter=FieldFilter('cliente', '==', cliente))
            docs = query.stream()

            for doc in docs:
                data = doc.to_dict()
                pallet = data.get('pallet', '')
                quantidade = data.get('quantidade', 0)
                if pallet in totais:
                    totais[pallet] += quantidade
            return totais

        except Exception as e:
            print(f"Erro ao buscar totais: {e}")
            return {}
    
    def on_pre_enter(self):
        # Preenche a data automaticamente ao entrar na tela
        super().on_pre_enter()
        self.ids.data_input_saida.text = datetime.now().strftime("%d/%m/%Y")

    def registrar_saidas(self):
        data = self.ids.data_input_saida.text.strip()
        cliente = self.ids.cliente_spinner_saida.text

        if not cliente or cliente == "Selecione um Cliente":
            self.mostrar_popup("Erro", "Selecione um cliente!")
            return

        erros = []
        db = FirebaseManager.get_instance().db
        totais = self.obter_totais_cliente(cliente)  # Busca os totais atuais

        for child in self.ids.pallets_container_saida.children:
            if isinstance(child, BoxLayout):
                lbl_pallet = None
                input_saida = None

                for widget in child.children:
                    if isinstance(widget, RoundedTextInput):
                        input_saida = widget
                    elif isinstance(widget, Label) and "Total:" not in widget.text:
                        lbl_pallet = widget
                    
                if lbl_pallet and input_saida:
                    pallet = lbl_pallet.text
                    total = totais.get(pallet, 0)
                    saida = input_saida.text.strip()
                
                    if not saida:
                        continue
                    
                    if not saida.isdigit():
                        erros.append(f"Quantidade inválida para {pallet}")
                        continue
                    
                    saida = int(saida)
                
                    if saida > total:
                        erros.append(f"Saída maior que o total ({pallet})")
                        continue
                    
                    try:
                        db.collection('registros').add({
                            'cliente': cliente,
                            'pallet': pallet,
                            'quantidade': -saida,
                            'data': data,
                            'timestamp': firestore.SERVER_TIMESTAMP
                        })
                    except Exception as e:
                        erros.append(f"Erro ao registrar {pallet}: {str(e)}")

        if erros:
            self.mostrar_popup("Erros", "\n".join(erros))
        else:
            self.mostrar_popup("Sucesso", "Saídas registradas com sucesso!")
            self.voltar_menu()

    def voltar_menu(self):
        self.ids.cliente_spinner_saida.text = "Selecione um Cliente"
        self.ids.pallets_container_saida.clear_widgets()
        self.ids.data_input_saida.text = ""

    def mostrar_popup(self, titulo, mensagem):
        content = BoxLayout(orientation='vertical', padding=10)

        lbl_mensagem = Label(
            text=mensagem,
            font_size=24,
            color=get_color_from_hex('#000000'),
            halign='center'
        )

        btn_ok = Button(
            text="OK",
            size_hint=(None, None),
            size=(dp(120), dp(40)),
            background_color=get_color_from_hex('#2E7D32'),
            color=get_color_from_hex('#FFFFFF'),
            pos_hint={'center_x': 0.5}
        )

        content.add_widget(lbl_mensagem)
        content.add_widget(btn_ok)

        popup = Popup(
            title=titulo,
            content=content,
            size_hint=(0.7, 0.4),
            separator_height=0,
            background_color=get_color_from_hex('#FFFFFF'),
            title_color=get_color_from_hex('#000000'),
            title_size='26sp'
        )

        btn_ok.bind(on_press=popup.dismiss)
        popup.open()


class TelaConsulta(Screen):
    registros = ListProperty([])
    totais = ListProperty([])

    # Adicionar inicialização do listener
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.listener = None

    def on_pre_enter(self):
        self.iniciar_listener()
        Clock.schedule_once(lambda dt: self.carregar_registros())

    def on_leave(self):
        if self.listener:
            self.listener.unsubscribe()

    def iniciar_listener(self):
        db = FirebaseManager.get_instance().db
        # Ordena por timestamp decrescente (registros mais novos primeiro)
        registros_ref = db.collection('registros').order_by('timestamp', direction=firestore.Query.DESCENDING)
        self.listener = registros_ref.on_snapshot(self.atualizar_registros)

    def atualizar_registros(self, snapshot, changes, read_time):
        registros_brutos = []
        for doc in snapshot:
            data = doc.to_dict()
            quantidade = int(data.get('quantidade', 0))
            tipo = "ENTRADA" if quantidade >= 0 else "SAÍDA"
            registros_brutos.append({
                'cliente': data.get('cliente', ''),
                'pallet': data.get('pallet', ''),
                'quantidade': quantidade,
                'tipo': tipo,
                'data': data.get('data', ''),
                'viewclass': 'RegistroConsultaItem'  # Obrigatório para RecycleView
            })

        self.processar_dados(registros_brutos)

    # Novo método unificado de processamento
    def processar_dados(self, registros_brutos):
        filtro = self.ids.busca_input.text.strip().lower()

        if self.ids.tabs.current_tab.text == 'Histórico Completo':
            registros_filtrados = self._filtrar_historico(registros_brutos, filtro)
            self.registros = [{
                'cliente': item['cliente'],
                'pallet': item['pallet'],
                'quantidade': str(item['quantidade']),
                'tipo': item['tipo'],
                'data': item['data'],
                'viewclass': 'RegistroConsultaItem'
            } for item in registros_filtrados]
            self.ids.rv_historico.data = self.registros

        elif self.ids.tabs.current_tab.text == 'Totais por Cliente':
            self.calcular_totais(registros_brutos, filtro)

    # Método simplificado de carregamento
    def carregar_registros(self, filtro=""):
        try:
            db = FirebaseManager.get_instance().db
            registros_ref = db.collection('registros').order_by('timestamp', direction=firestore.Query.DESCENDING)
            docs = registros_ref.stream()

            registros_brutos = []
            for doc in docs:
                data = doc.to_dict()
                quantidade = int(data.get('quantidade', 0))
                tipo = "ENTRADA" if quantidade >= 0 else "SAÍDA"
                registros_brutos.append({
                    'cliente': data.get('cliente', ''),
                    'pallet': data.get('pallet', ''),
                    'quantidade': quantidade,
                    'tipo': tipo,
                    'data': data.get('data', '')
                })

            self.processar_dados(registros_brutos)  # Reutiliza o processamento

        except Exception as e:
            print(f"Erro na consulta: {e}")

    # Filtro unificado
    def _filtrar_historico(self, registros, filtro):
        if not filtro:
            return registros

        filtro_lower = filtro.lower()
        return [r for r in registros if
                filtro_lower in r['cliente'].lower() or
                filtro_lower in r['pallet'].lower() or
                filtro_lower in r['data'].lower() or
                filtro_lower in str(r['quantidade']).lower() or
                filtro_lower in r['tipo'].lower()
            ]

    def calcular_totais(self, registros_brutos, filtro=""):
        try:
            totais_dict = {}
        
            # Processamento manual
            for registro in registros_brutos:
                quantidade = int(registro['quantidade'])
                chave = (registro['cliente'], registro['pallet'])
                totais_dict[chave] = totais_dict.get(chave, 0) + registro['quantidade']
        
            # Formatação dos resultados
            self.totais = [{
                'cliente': cliente,
                'pallet': pallet,
                'total': str(total),
                'viewclass': 'TotalItem'
            } for (cliente, pallet), total in totais_dict.items()]

            self.ids.rv_totais.data = self.totais

        except Exception as e:
            print(f"Erro ao calcular totais: {e}")

    # Filtro específico para totais
    def _filtro_totais(self, item, filtro):
        if not filtro:
            return True
        return any(
            filtro in str(valor).lower()
            # Converter quantidade
            for valor in [item['cliente'], item['pallet'], str(item['quantidade'])]
        )

    # Método de mudança de aba atualizado
    def on_tab_change(self, instance, value):
        if value and value.text in ['Histórico Completo', 'Totais por Cliente']:
            self.carregar_registros()


class PalletApp(App):

    def build(self):
        FirebaseManager.get_instance()

        self.client_manager = ClientManager()
        sm = ScreenManager()
        sm.add_widget(TelaInicial(name='inicio'))
        sm.add_widget(TelaRegistro(name='registro'))
        sm.add_widget(TelaConsulta(name='consulta'))
        sm.add_widget(TelaSaida(name='saida'))
        return sm

    def on_start(self):
        # Garanta que o client_manager está vinculado
        self.root.get_screen('registro').client_manager = self.client_manager


if __name__ == '__main__':
    PalletApp().run()
