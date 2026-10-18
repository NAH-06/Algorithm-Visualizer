import osmnx as ox

# Tọa độ trung tâm của Học viện Công nghệ Bưu chính Viễn thông
ptit_location = (20.980816, 105.787358)

# Tải đồ thị đường đi bộ trong bán kính 800m
G = ox.graph_from_point(ptit_location, dist=800, network_type='walk')

# Lưu lại thành file offline để sử dụng cho Web Backend
ox.save_graphml(G, "ptit_campus.graphml")
print("Đã tải và lưu thành công cấu trúc bản đồ!")