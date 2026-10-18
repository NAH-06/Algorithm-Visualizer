from flask import Flask, jsonify, render_template, request
import sys
import osmnx as ox
import networkx as nx

app = Flask(__name__)

# Tọa độ trung tâm PTIT
PTIT_COORD = (20.980816, 105.787358)

# Tải file bản đồ offline hoặc tự động tải mới bán kính 5km
try:
    print("Đang kiểm tra dữ liệu bản đồ...")
    G_osm = ox.load_graphml("ptit_5km.graphml")
    print("Đã tải thành công file ptit_5km.graphml (Bán kính 5km quanh PTIT)!")
except:
    print("Chưa có file bản đồ 5km. Đang tiến hành tải từ OpenStreetMap...")
    print("LƯU Ý: Quá trình này có thể mất 1-3 phút cho lần chạy đầu tiên. Vui lòng không tắt terminal...")
    try:
        # Tải bản đồ bán kính 5000m (5km) quanh PTIT
        G_osm = ox.graph_from_point(PTIT_COORD, dist=5000, network_type='all')
        ox.save_graphml(G_osm, "ptit_5km.graphml")
        print("Đã tải và lưu bản đồ thành công vào ptit_5km.graphml!")
    except Exception as e:
        G_osm = None
        print(f"Cảnh báo: Không thể tải bản đồ. Lỗi: {e}")

# Hàm hỗ trợ lấy tên địa điểm cho thông báo Đồ thị
def get_node_name(idx, is_map):
    if idx == -1: return ""
    names_map = ['Cổng Chính', 'Căn Tin', 'Tòa nhà A1', 'Thư Viện', 'Sân Bóng', 'Ký Túc Xá', 'Nhà Xe']
    names_basic = ['A', 'B', 'C', 'D', 'E']
    try: return names_map[idx] if is_map else names_basic[idx]
    except: return str(idx)

# ==========================================
# PHẦN 1: CÁC THUẬT TOÁN SẮP XẾP
# ==========================================
def bubble_sort_states(arr):
    states = []; n = len(arr); states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Bắt đầu Bubble Sort'}) 
    for i in range(n):
        for j in range(0, n-i-1):
            states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [j, j+1], 'msg': f'So sánh {arr[j]} và {arr[j+1]}'}) 
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
                states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [j, j+1], 'msg': f'Đổi chỗ vì {arr[j+1]} < {arr[j]}'}) 
    states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Sắp xếp hoàn tất!'}); return states

def selection_sort_states(arr):
    states = []; n = len(arr); states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Bắt đầu Selection Sort'})
    for i in range(n):
        min_idx = i
        for j in range(i+1, n):
            states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [min_idx, j], 'msg': f'Tìm min: Đang xét {arr[j]}'})
            if arr[min_idx] > arr[j]: 
                min_idx = j
                states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [min_idx], 'msg': f'Min tạm thời là {arr[min_idx]}'})
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
        states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [i, min_idx], 'msg': f'Chốt min {arr[i]}, đổi chỗ về đầu đoạn'})
    states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Sắp xếp hoàn tất!'}); return states

def insertion_sort_states(arr):
    states = []; n = len(arr); states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Bắt đầu Insertion Sort'})
    for i in range(1, n):
        key = arr[i]; j = i - 1
        states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [i], 'msg': f'Lấy {key} ra để chèn'})
        while j >= 0 and key < arr[j]:
            arr[j + 1] = arr[j]; j -= 1
            states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [j+1, max(0, j)], 'msg': f'Dời {arr[j+1]} sang phải'})
        arr[j + 1] = key; states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [j+1], 'msg': f'Chèn {key} vào vị trí'})
    states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Sắp xếp hoàn tất!'}); return states

def quick_sort_states(arr):
    states = []; states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Bắt đầu Quick Sort'})
    def partition(low, high):
        pivot = arr[high]; i = low - 1
        for j in range(low, high):
            states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [j, high], 'msg': f'So sánh {arr[j]} với chốt (pivot) {pivot}'}) 
            if arr[j] < pivot:
                i = i + 1; arr[i], arr[j] = arr[j], arr[i]
                states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [i, j], 'msg': f'Đổi chỗ {arr[i]} và {arr[j]}'})
        arr[i + 1], arr[high] = arr[high], arr[i + 1]
        states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [i + 1, high], 'msg': f'Đưa chốt {pivot} về vị trí đúng'})
        return i + 1
    def quick_sort_recursive(low, high):
        if low < high:
            pi = partition(low, high)
            quick_sort_recursive(low, pi - 1)
            quick_sort_recursive(pi + 1, high)
    quick_sort_recursive(0, len(arr) - 1)
    states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Sắp xếp hoàn tất!'}); return states

def merge_sort_states(arr):
    states = []; states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Bắt đầu Merge Sort'})
    def merge(left, mid, right):
        temp = []; i, j = left, mid + 1
        while i <= mid and j <= right:
            states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [i, j], 'msg': f'Đang trộn: So sánh {arr[i]} và {arr[j]}'})
            if arr[i] <= arr[j]: temp.append(arr[i]); i += 1
            else: temp.append(arr[j]); j += 1
        while i <= mid: temp.append(arr[i]); i += 1
        while j <= right: temp.append(arr[j]); j += 1
        for k in range(len(temp)):
            arr[left + k] = temp[k]; states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [left + k], 'msg': f'Ghi đè {temp[k]} vào mảng chính'})
    def merge_sort_recursive(left, right):
        if left < right:
            mid = (left + right) // 2
            merge_sort_recursive(left, mid)
            merge_sort_recursive(mid + 1, right)
            merge(left, mid, right)
    merge_sort_recursive(0, len(arr) - 1)
    states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Sắp xếp hoàn tất!'}); return states

def radix_sort_states(arr):
    states = []; states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Bắt đầu Radix Sort'})
    if not arr: return states
    max_val = max(arr); exp = 1
    while max_val // exp > 0:
        n = len(arr); output = [0] * n; count = [0] * 10
        for i in range(n):
            index = arr[i] // exp; count[index % 10] += 1
            states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [i], 'msg': f'Xét chữ số hàng {exp} của {arr[i]} = {index%10}'})
        for i in range(1, 10): count[i] += count[i - 1]
        i = n - 1
        while i >= 0:
            index = arr[i] // exp; output[count[index % 10] - 1] = arr[i]
            count[index % 10] -= 1; i -= 1
        for i in range(n):
            arr[i] = output[i]
            states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [i], 'msg': f'Chuyển {arr[i]} vào vị trí mới'})
        exp *= 10
    states.append({'type': 'sorting', 'array': list(arr), 'active_indices': [], 'msg': 'Sắp xếp hoàn tất!'}); return states

# ==========================================
# PHẦN 2: CÁC THUẬT TOÁN ĐỒ THỊ
# ==========================================
GRAPH_BASIC_NODES = 5
GRAPH_BASIC_EDGES = [(0, 1, 4), (0, 2, 2), (1, 2, 5), (1, 3, 10), (2, 3, 3), (3, 4, 7)]
GRAPH_MAP_NODES = 7
GRAPH_MAP_EDGES = [
    (0, 1, 50), (0, 2, 80), (1, 2, 40), (1, 3, 120), 
    (2, 4, 70), (3, 4, 60), (3, 5, 90), (4, 5, 110), 
    (4, 6, 85), (5, 6, 30)
]

def get_adj_list(num_nodes, edges):
    adj = {i: [] for i in range(num_nodes)}
    for u, v, w in edges: adj[u].append(v); adj[v].append(u)
    for i in range(num_nodes): adj[i].sort()
    return adj

def get_neighbors_with_weights(u, edges):
    res = []
    for edge in edges:
        n1, n2, w = edge
        if n1 == u: res.append((n2, w))
        elif n2 == u: res.append((n1, w))
    return res

def reconstruct_path(parent_array, target_node):
    path = []
    if target_node != -1 and parent_array[target_node] != -1:
        curr = target_node
        while parent_array[curr] != -1:
            path.append((parent_array[curr], curr))
            curr = parent_array[curr]
    return path

def dijkstra_states(num_nodes, edges, target_node, is_map):
    states = []; dist = [sys.maxsize] * num_nodes; dist[0] = 0; visited = [False] * num_nodes; parent = [-1] * num_nodes
    graph_matrix = [[0]*num_nodes for _ in range(num_nodes)]
    for u, v, w in edges: graph_matrix[u][v] = w; graph_matrix[v][u] = w
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': 'Bắt đầu Dijkstra: Tìm đường ngắn nhất'})
    for _ in range(num_nodes):
        u = -1; min_dist = sys.maxsize
        for i in range(num_nodes):
            if not visited[i] and dist[i] < min_dist: min_dist = dist[i]; u = i
        if u == -1: break
        visited[u] = True
        u_name = get_node_name(u, is_map)
        states.append({'type': 'graph', 'active_node': u, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Đang xét địa điểm: {u_name}'})
        for v in range(num_nodes):
            if graph_matrix[u][v] > 0 and not visited[v] and dist[v] > dist[u] + graph_matrix[u][v]:
                dist[v] = dist[u] + graph_matrix[u][v]; parent[v] = u
                v_name = get_node_name(v, is_map)
                states.append({'type': 'graph', 'active_node': v, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Cập nhật khoảng cách đến {v_name} là {dist[v]}'})
    final_path = reconstruct_path(parent, target_node)
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'final_path': final_path, 'msg': 'Đã hoàn tất tìm đường!'})
    return states

def bfs_states(num_nodes, edges, target_node, is_map):
    states = []; visited = [False] * num_nodes; dist = [sys.maxsize] * num_nodes; parent = [-1] * num_nodes
    adj = get_adj_list(num_nodes, edges); queue = [0]; visited[0] = True; dist[0] = 0
    states.append({'type': 'graph', 'active_node': 0, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': 'Bắt đầu BFS: Loang dần theo cấp độ'})
    while queue:
        u = queue.pop(0)
        u_name = get_node_name(u, is_map)
        states.append({'type': 'graph', 'active_node': u, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Rút {u_name} ra khỏi hàng đợi'})
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True; dist[v] = dist[u] + 1; parent[v] = u; queue.append(v)
                v_name = get_node_name(v, is_map)
                states.append({'type': 'graph', 'active_node': v, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Thăm {v_name}, cách {dist[v]} bước'})
    final_path = reconstruct_path(parent, target_node)
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'final_path': final_path, 'msg': 'Hoàn tất quét BFS!'})
    return states

def dfs_states(num_nodes, edges, target_node, is_map):
    states = []; visited = [False] * num_nodes; dist = [sys.maxsize] * num_nodes; parent = [-1] * num_nodes
    adj = get_adj_list(num_nodes, edges)
    def dfs(u, step):
        visited[u] = True; dist[u] = step
        u_name = get_node_name(u, is_map)
        states.append({'type': 'graph', 'active_node': u, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Khám phá {u_name}'})
        for v in adj[u]:
            if not visited[v]:
                parent[v] = u
                v_name = get_node_name(v, is_map)
                states.append({'type': 'graph', 'active_node': u, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Từ {u_name} đi sâu xuống {v_name}'})
                dfs(v, step + 1)
                states.append({'type': 'graph', 'active_node': u, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Quay lui (Backtrack) về {u_name}'})
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': 'Bắt đầu DFS: Ưu tiên đi sâu'})
    dfs(0, 0)
    final_path = reconstruct_path(parent, target_node)
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'final_path': final_path, 'msg': 'Hoàn tất duyệt DFS!'})
    return states

def bellman_ford_states(num_nodes, edges, target_node, is_map):
    states = []; dist = [sys.maxsize] * num_nodes; dist[0] = 0; visited = [False] * num_nodes; parent = [-1] * num_nodes; visited[0] = True
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': 'Bắt đầu Bellman-Ford'})
    for i in range(num_nodes - 1):
        updated = False
        states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'--- Quét toàn bộ cạnh lần {i+1} ---'})
        for u, v, w in edges:
            if dist[u] != sys.maxsize and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w; visited[v] = True; parent[v] = u; updated = True
                states.append({'type': 'graph', 'active_node': v, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Cập nhật {get_node_name(v, is_map)} qua {get_node_name(u, is_map)}'})
            if dist[v] != sys.maxsize and dist[v] + w < dist[u]:
                dist[u] = dist[v] + w; visited[u] = True; parent[u] = v; updated = True
                states.append({'type': 'graph', 'active_node': u, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': f'Cập nhật {get_node_name(u, is_map)} qua {get_node_name(v, is_map)}'})
        if not updated: break
    final_path = reconstruct_path(parent, target_node)
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'final_path': final_path, 'msg': 'Hoàn tất Bellman-Ford'})
    return states

def prim_states(num_nodes, edges, is_map):
    states = []; key = [sys.maxsize] * num_nodes; in_mst = [False] * num_nodes; key[0] = 0; mst_edges = []; parent = [-1] * num_nodes
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(in_mst), 'dist': list(key), 'edges': edges, 'msg': 'Bắt đầu thuật toán Prim (Tạo Cây Khung)'})
    for _ in range(num_nodes):
        u = -1; min_val = sys.maxsize
        for i in range(num_nodes):
            if not in_mst[i] and key[i] < min_val: min_val = key[i]; u = i
        if u == -1: break
        in_mst[u] = True
        if parent[u] != -1: mst_edges.append((parent[u], u))
        
        u_name = get_node_name(u, is_map)
        states.append({'type': 'graph', 'active_node': u, 'visited': list(in_mst), 'dist': list(key), 'edges': edges, 'msg': f'Thêm {u_name} vào Cây khung'})
        for v, w in get_neighbors_with_weights(u, edges):
            if not in_mst[v] and w < key[v]:
                key[v] = w; parent[v] = u
                v_name = get_node_name(v, is_map)
                states.append({'type': 'graph', 'active_node': v, 'visited': list(in_mst), 'dist': list(key), 'edges': edges, 'msg': f'Nối {u_name} tới {v_name} chi phí {w}'})
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(in_mst), 'dist': list(key), 'edges': edges, 'final_path': mst_edges, 'msg': 'Đã hoàn thành Cây khung nhỏ nhất!'})
    return states

def kruskal_states(num_nodes, edges, is_map):
    states = []; parent = list(range(num_nodes))
    def find(i):
        if parent[i] == i: return i
        parent[i] = find(parent[i]); return parent[i]
    sorted_edges = sorted(edges, key=lambda item: item[2])
    visited = [False] * num_nodes; dist = [0] * num_nodes; mst_edges = []
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'msg': 'Bắt đầu Kruskal: Đã sắp xếp các cạnh tăng dần'})
    for u, v, w in sorted_edges:
        visited[u] = True; visited[v] = True
        u_name = get_node_name(u, is_map); v_name = get_node_name(v, is_map)
        states.append({'type': 'graph', 'active_node': u, 'visited': list(visited), 'dist': [w]*num_nodes, 'edges': edges, 'msg': f'Xét cạnh {u_name} - {v_name} (CP: {w})'})
        root_u = find(u); root_v = find(v)
        if root_u != root_v:
            parent[root_u] = root_v; mst_edges.append((u, v))
            states.append({'type': 'graph', 'active_node': v, 'visited': list(visited), 'dist': [w]*num_nodes, 'edges': edges, 'msg': f'Chọn cạnh {u_name} - {v_name} vào Cây khung'})
        else:
            states.append({'type': 'graph', 'active_node': v, 'visited': list(visited), 'dist': [w]*num_nodes, 'edges': edges, 'msg': f'Bỏ qua cạnh {u_name} - {v_name} vì tạo chu trình'})
    states.append({'type': 'graph', 'active_node': -1, 'visited': list(visited), 'dist': list(dist), 'edges': edges, 'final_path': mst_edges, 'msg': 'Đã hoàn thành Cây khung nhỏ nhất!'})
    return states

# ==========================================
# PHẦN 3: ROUTER API
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/api/route_osm', methods=['POST'])
def route_osm():
    if G_osm is None:
        return jsonify({'error': 'Chưa tải được dữ liệu bản đồ.'})
        
    data = request.get_json()
    start = data.get('start')
    end = data.get('end')
    
    # Tìm đỉnh gần nhất với tọa độ click
    orig_node = ox.distance.nearest_nodes(G_osm, X=start[1], Y=start[0])
    dest_node = ox.distance.nearest_nodes(G_osm, X=end[1], Y=end[0])
    
    try:
        # Tính toán độ dài tối ưu và truy vết đường đi (Dijkstra)
        total_length = nx.shortest_path_length(G_osm, orig_node, dest_node, weight='length')
        route = nx.shortest_path(G_osm, orig_node, dest_node, weight='length')
        
        path_coords = [[G_osm.nodes[node]['y'], G_osm.nodes[node]['x']] for node in route]
        
        return jsonify({
            'path': path_coords,
            'distance': round(total_length, 1), # Trả về tổng chiều dài (mét)
            'nodes_count': len(route)           # Trả về số lượng đỉnh
        })
    except nx.NetworkXNoPath:
        return jsonify({'error': 'Không tìm thấy đường đi kết nối 2 điểm này.'})
    except Exception as e:
        return jsonify({'error': f'Lỗi hệ thống: {str(e)}'})

@app.route('/api/run', methods=['POST'])
def run_algorithm():
    data = request.get_json()
    category = data.get('category', 'sorting')
    graph_type = data.get('graph_type', 'basic') 
    algo = data.get('algorithm', 'bubble')
    input_str = data.get('array', '')
    target_node = int(data.get('target', -1))

    if category == 'graph':
        is_map = (graph_type == 'map')
        if graph_type == 'basic':
            num_nodes = GRAPH_BASIC_NODES; edges = GRAPH_BASIC_EDGES
        else:
            num_nodes = GRAPH_MAP_NODES; edges = GRAPH_MAP_EDGES

        if algo == 'bfs': states = bfs_states(num_nodes, edges, target_node, is_map)
        elif algo == 'dfs': states = dfs_states(num_nodes, edges, target_node, is_map)
        elif algo == 'bellman': states = bellman_ford_states(num_nodes, edges, target_node, is_map)
        elif algo == 'prim': states = prim_states(num_nodes, edges, is_map)
        elif algo == 'kruskal': states = kruskal_states(num_nodes, edges, is_map)
        else: states = dijkstra_states(num_nodes, edges, target_node, is_map)
        return jsonify(states)

    try: arr = [int(x.strip()) for x in input_str.split(',')]
    except: arr = [50, 20, 80, 40, 90, 10, 30, 70, 60]

    if algo == 'selection': states = selection_sort_states(arr)
    elif algo == 'insertion': states = insertion_sort_states(arr)
    elif algo == 'quick': states = quick_sort_states(arr)
    elif algo == 'merge': states = merge_sort_states(arr)
    elif algo == 'radix': states = radix_sort_states(arr)
    else: states = bubble_sort_states(arr)
        
    return jsonify(states) 

if __name__ == '__main__':
    app.run(debug=True)