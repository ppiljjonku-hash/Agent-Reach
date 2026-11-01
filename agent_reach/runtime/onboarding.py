"""Read-only session discovery and explicit connection choices. Never logs a user in."""
from datetime import datetime

# These describe public routes an agent can try, not authenticated Reach readiness.
# A successful sample depends on the tool, network exit, content and platform response.
_PUBLIC_ACCESS = {
    'youtube': '公开搜索、简介可先读；原生工具的部分样本可取评论、字幕和时间戳。',
    'reddit': '公开搜索、正文和部分评论可先读；部分公开 JSON 样本可含评论及 parent_id。',
    'twitter': 'X의 검색·프로필·타임라인·답글은 로컬 브라우저의 사이트 도구로 읽습니다.',
}

_CAPABILITY_LIMITS = {
    'youtube': ['read 返回元信息和简介；没有独立 comments 动作。',
                '字幕依赖可用轨道；转录还需配置服务及额度，登录不保证有字幕。'],
    'reddit': ['read 仅承诺其返回的帖子和评论；不保证完整评论树，不提供发评论动作。'],
    'twitter': ['thread 仅覆盖实际返回的回复；不保证完整评论流，不提供发帖动作。'],
}


# Public web options and authenticated Reach actions; detailed limits stay in capability_summary.
_QUICK_ACCESS = {
    'youtube': ('✅ 找视频、读简介、读字幕', '—'),
    'reddit': ('✅ 搜帖子、读正文、看评论', '—'),
    'twitter': ('사이트 접근 권한에 따라 다름', '검색·프로필·타임라인·답글'),
}

_DISPLAY_NAMES = {
    'youtube': 'YouTube', 'reddit': 'Reddit', 'twitter': 'X / Twitter',
}

_STATUS_LABELS = {
    'not_added': '未接入，可按需添加', 'needs_setup': '待配置', 'unverified': '已接入，待实测',
    'ready': '已有有效验收', 'search_ready': '仅搜索已有验收',
    'needs_login': '所测动作要求登录', 'cooldown': '暂缓访问',
    'needs_user_action': '等待人工验证', 'broken': '当前路径故障',
}


def _local_greeting():
    """Use the installing computer's clock and timezone, without a network lookup."""
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return '早上好呀，想搜点什么？☀️'
    if 11 <= hour < 14:
        return '中午好，想搜点什么？'
    if 14 <= hour < 18:
        return '下午好，想搜点什么？'
    if 18 <= hour < 22:
        return '晚上好，想搜点什么？'
    return '夜深了，想搜点什么？🌙'

def _upgrade_lines(result):
    """Only for users coming from 1.5: what was kept, what changed, what is left to do."""
    migration = result.get('migration')
    if not migration:
        return []
    lines = ['**这次是从旧版本（1.5）升级上来的：**', '',
             '- 你的密钥和设置都保留了。',
             '- X·Reddit·YouTube만 지원합니다.',
             '- 검색어와 URL은 제3자 검색 서비스에 보내지 않습니다.']
    suggested = [_DISPLAY_NAMES.get(n, n) for n in migration.get('suggested_channels') or []]
    if suggested:
        lines.append('- 你以前用过' + '、'.join(suggested) + '，想继续用直接跟我说"加上 XX"。')
    old = result.get('old_copies') or {}
    if old.get('removed'):
        lines.append('- 旧版程序已经删掉，以后不会和新版冲突。')
    for item in old.get('failed') or []:
        from .legacy import manual_command
        lines.append(f"- 旧版程序没删成，请运行：`{manual_command(item)}`")
    return lines + ['']



def installation_report(result):
    """Render one short receipt; keep detailed evidence in the structured summary."""
    def cell(value):
        return str(value).replace('|', r'\|').replace('\n', ' ')

    entries = result['capability_summary']['channels']
    installs = {row['channel']: row for row in result['default_channels']}
    installed = sum(bool(row['ok']) for row in installs.values())
    completed = all(row['ok'] for row in installs.values())
    lines = [
        _local_greeting(), '',
        f"**Agent Reach {result['version']} {'安装完成' if completed else '安装还差一步'}。** "
        f'默认功能：{installed}/{len(installs)} 项准备成功。', '',
        *_upgrade_lines(result),
        '✅ 不用登录；❌ 登录后再试；🔑 需 Key；— 不用额外登录。', '',
        '| 平台 | 不登录可以查什么 | 需要登录后再试 |', '|---|---|---|',
    ]
    for entry in sorted(entries, key=lambda item: item['level'] != 'default'):
        name = entry['channel']
        label = _DISPLAY_NAMES.get(name, name)
        item = installs.get(name)
        if entry['level'] == 'default':
            if item and not item['ok']:
                label += '（安装失败：' + item.get('error', {}).get('code', 'UNKNOWN') + '）'
            elif not item:
                label += '（保留用户移除）'
        elif entry['reach_status'] in {'needs_setup', 'needs_login', 'cooldown', 'needs_user_action', 'broken'}:
            label += '（' + _STATUS_LABELS[entry['reach_status']] + '）'
        public, login = _QUICK_ACCESS.get(name, (entry['public_access'], '—'))
        lines.append('| ' + ' | '.join(cell(value) for value in (label, public, login)) + ' |')
    verified = [entry for entry in entries if entry['verified_actions']]
    if verified:
        names = '；'.join(_DISPLAY_NAMES.get(entry['channel'], entry['channel']) + '：' +
                         '/'.join(entry['verified_actions']) for entry in verified)
        lines += ['', '已测通过：' + names + '。其余还没逐项联网测试。']
    else:
        lines += ['', '还没逐项联网测试。']
    lines += ['각 사이트의 로컬 도구만 사용합니다. 댓글과 자막은 실제 반환 범위만 보장합니다.', '',
              '**想查什么，直接说。** 会先尝试复用已有登录；确实需要你登录时，再打开窗口。']
    return '\n'.join(lines) + '\n'



def capability_summary(channels, statuses):
    """Describe public options, declared actions and local evidence without any I/O.

    Management supplies status records so this summary cannot initiate discovery,
    installation, login or a live request. Actions always come from the registry.
    """
    by_name = {entry['channel']: entry for entry in statuses}
    entries = []
    for ch in channels:
        current = by_name.get(ch.name, {})
        names = [action.name for action in ch.actions]
        can_login = bool(ch.login_url or ch.login_argv)
        auth_actions = names if can_login else []
        entries.append({
            'channel': ch.name,
            'level': ch.level,
            'reach_status': current.get('status', 'unverified'),
            'verified_actions': current.get('verified_actions', []),
            'actions': [{'action': action.name, 'detail': action.help} for action in ch.actions],
            'public_access': _PUBLIC_ACCESS.get(ch.name, '로컬 사이트 도구를 사용합니다.'),
            'authentication': {
                'when': 'only_if_required',
                'may_enable_actions': [name for name in auth_actions if name in names],
                'note': '剩余任务的选定路径实际要求认证时，先复用已授权会话，再请用户登录；登录后仍需验证动作。',
            },
            'limits': _CAPABILITY_LIMITS.get(ch.name, []),
        })
    message = ['각 사이트의 로컬 도구를 사용합니다. 필요한 경우에만 사용자가 로그인합니다.']
    for entry in entries:
        actions = '/'.join(action['action'] for action in entry['actions'])
        status_label = _STATUS_LABELS.get(entry['reach_status'], entry['reach_status'])
        limits = ' '.join(entry['limits'])
        message.append(f"{entry['channel']}：{entry['public_access']} Reach {actions}（{status_label}）。{limits}")
    return {
        'policy': 'site_tools_only; login_only_when_required',
        'evidence_note': '公开路径说明来自样本与访问条件，不能代替本机 Reach 验收；网络、403、超时或验证码均不能单独证明需要登录。',
        'channels': entries,
        'message': '\n'.join(message),
    }
